"""FinWell AI - PDF-driven internal-transfer and multi-account integration test.

Processes the two real November statement PDFs through the existing
PDF preprocessing pipeline, then passes the resulting validated records
into the existing reconciliation services.

Safety:
- No MySQL writes
- No ChromaDB writes
- No transaction storage
- No reconciliation case creation
- Account/transaction IDs below are temporary in-memory test identifiers

Run from the FinWell_AI project root:
    python .\\tests\\run_pdf_internal_transfer_integration.py

Place this file at:
    tests/run_pdf_internal_transfer_integration.py
"""

import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pdf_extraction.pdf_validator import validate_pdf
from pdf_extraction.pdf_reader import extract_pdf_text
from pdf_extraction.document_classifier import classify_document

from preprocessing.text_cleaner import clean_extracted_text
from preprocessing.transaction_parser import parse_transactions
from preprocessing.data_normalizer import normalize_transactions
from preprocessing.data_validator import validate_transactions

from reconciliation.internal_transfer_matcher import reconcile_internal_transfers
from reconciliation.multi_account_reconciler import reconcile_multiple_accounts


PRIMARY_PDF = Path(
    r"C:\Users\shaas\Downloads\finwell_reconciliation_primary_nov2026.pdf"
)
SECONDARY_PDF = Path(
    r"C:\Users\shaas\Downloads\finwell_reconciliation_secondary_nov2026.pdf"
)

# Temporary IDs only. These are not written to MySQL.
TEST_USER_ID = 9001
PRIMARY_ACCOUNT_ID = 9101
SECONDARY_ACCOUNT_ID = 9102

# Independent expected statement results. These are used only for assertions,
# never as transaction input to either reconciliation engine.
EXPECTED = {
    "primary": {
        "account_suffix": "4821",
        "transaction_count": 14,
        "total_debit": 15799.00,
        "total_credit": 41650.00,
        "external_income": 41650.00,
        "external_expenses": 10799.00,
        "internal_transfer_debits": 5000.00,
        "internal_transfer_credits": 0.00,
        "opening_balance": 50000.00,
        "opening_balance_estimate": 50000.00,
        "closing_balance": 75851.00,
    },
    "secondary": {
        "account_suffix": "7392",
        "transaction_count": 5,
        "total_debit": 2950.00,
        "total_credit": 13000.00,
        "external_income": 8000.00,
        "external_expenses": 2950.00,
        "internal_transfer_debits": 0.00,
        "internal_transfer_credits": 5000.00,
        "opening_balance": 20000.00,
        "opening_balance_estimate": 20000.00,
        "closing_balance": 30050.00,
    },
}

EXPECTED_CONSOLIDATED = {
    "external_income": 49650.00,
    "external_expenses": 13749.00,
    "net_external_cash_flow": 35901.00,
    "internal_transfer_debits": 5000.00,
    "internal_transfer_credits": 5000.00,
    "opening_balance_estimate": 70000.00,
    "closing_balance": 105901.00,
}


def require(condition, message):
    """Raise a clear error instead of silently accepting a failed check."""
    if not condition:
        raise AssertionError(message)


def process_pdf(label, pdf_path, account_id):
    print("\n" + "=" * 70)
    print(f"PROCESSING PDF: {label.upper()} — {pdf_path.name}")
    print("=" * 70)

    if not pdf_path.is_file():
        raise FileNotFoundError(f"Statement PDF not found: {pdf_path}")

    # 1. Validate PDF.
    pdf_check = validate_pdf(str(pdf_path))
    print("\n[1] PDF VALIDATION")
    print(json.dumps(pdf_check, indent=2, default=str))
    require(pdf_check.get("valid") is True, f"PDF validation failed: {pdf_path}")

    # 2. Extract text.
    extraction = extract_pdf_text(str(pdf_path))
    require(
        extraction.get("success") is True,
        extraction.get("error", f"PDF extraction failed: {pdf_path}"),
    )
    extracted_text = extraction.get("full_text", "")
    require(bool(extracted_text.strip()), f"No selectable text in {pdf_path}")

    # 3. Verify account identity from source PDF before assigning account ID.
    digits = re.sub(r"\D", "", extracted_text)
    expected_suffix = EXPECTED[label]["account_suffix"]
    require(
        expected_suffix in digits,
        f"Expected account suffix {expected_suffix} not found in {pdf_path.name}",
    )
    require(
        "ARJUN KUMAR" in extracted_text.upper(),
        f"Expected account holder ARJUN KUMAR not found in {pdf_path.name}",
    )

    # 4. Clean extracted text using the existing ingestion cleaner.
    cleaning = clean_extracted_text(extracted_text)
    require(
        isinstance(cleaning, dict) and cleaning.get("success") is True,
        cleaning.get("error", "Text cleaning failed")
        if isinstance(cleaning, dict)
        else "Unexpected text-cleaner response",
    )
    cleaned_text = cleaning.get("cleaned_text", "")
    require(bool(cleaned_text.strip()), "Text cleaner returned empty text")

    # 5. Classify document using existing classifier.
    classification = classify_document(cleaned_text)
    require(
        classification.get("success") is True,
        classification.get("error", "Document classification failed"),
    )

    # 6. Parse transactions from PDF-derived text.
    parsing = parse_transactions(cleaned_text)
    require(
        parsing.get("success") is True,
        parsing.get("error", "Transaction parsing failed"),
    )
    parsed = parsing.get("transactions", [])

    # 7. Normalize parsed transactions.
    normalization = normalize_transactions(parsed)
    require(
        normalization.get("success") is True,
        normalization.get("error", "Transaction normalization failed"),
    )
    normalized = normalization.get("transactions", [])

    # 8. Validate normalized transactions.
    validation = validate_transactions(normalized)
    require(
        validation.get("success") is True,
        validation.get("error", "Transaction validation failed"),
    )

    valid = validation.get("valid_transactions", [])
    invalid = validation.get("invalid_transactions", [])
    invalid_count = validation.get("invalid_count", len(invalid))

    print("\n[2] PDF-DERIVED PIPELINE COUNTS")
    print("Document type:", classification.get("document_type"))
    print("Pages:", extraction.get("total_pages"))
    print("Parsed:", len(parsed))
    print("Normalized:", len(normalized))
    print("Valid:", len(valid))
    print("Invalid:", invalid_count)

    # Do not silently drop invalid rows from a financial reconciliation.
    require(
        invalid_count == 0 and not invalid,
        "Invalid transactions found; refusing to reconcile an incomplete statement.\n"
        + json.dumps(invalid, indent=2, default=str),
    )

    # 9. Assign temporary in-memory account identity and currency.
    # Transaction content itself remains the parser/normalizer output.
    enriched = []
    for index, transaction in enumerate(valid, start=1):
        item = dict(transaction)
        item["transaction_id"] = None  # temporary identity assigned below
        item["user_id"] = TEST_USER_ID
        item["account_id"] = account_id
        item["currency"] = str(item.get("currency") or "INR").upper()

        if not item.get("date"):
            item["date"] = item.get("transaction_date")
        require(item.get("date") is not None, f"Missing date in {label} row {index}")

        # Multi-account balance reporting depends on the parsed running balance.
        require(
            item.get("balance") is not None,
            f"Missing running balance in {label} row {index}; cannot verify balance consolidation.",
        )
        enriched.append(item)

    total_debit = round(sum(float(row.get("debit") or 0) for row in enriched), 2)
    total_credit = round(sum(float(row.get("credit") or 0) for row in enriched), 2)

    print("\n[3] VALIDATED PDF-DERIVED TRANSACTIONS")
    for index, row in enumerate(enriched, start=1):
        print(
            f"{index:02d}. Date={row.get('date')} | "
            f"Description={row.get('description')} | "
            f"Debit={row.get('debit')} | Credit={row.get('credit')} | "
            f"Balance={row.get('balance')}"
        )

    expected = EXPECTED[label]
    require(len(enriched) == expected["transaction_count"],
            f"{label}: expected {expected['transaction_count']} rows, got {len(enriched)}")
    require(total_debit == expected["total_debit"],
            f"{label}: debit total mismatch: {total_debit}")
    require(total_credit == expected["total_credit"],
            f"{label}: credit total mismatch: {total_credit}")

    return {
        "label": label,
        "account_id": account_id,
        "filename": pdf_path.name,
        "transactions": enriched,
        "parsed_count": len(parsed),
        "normalized_count": len(normalized),
        "valid_count": len(valid),
        "invalid_count": invalid_count,
        "total_debit": total_debit,
        "total_credit": total_credit,
    }


def main():
    # Process both actual statement PDFs.
    primary = process_pdf("primary", PRIMARY_PDF, PRIMARY_ACCOUNT_ID)
    secondary = process_pdf("secondary", SECONDARY_PDF, SECONDARY_ACCOUNT_ID)

    # Temporary account metadata, derived only after verifying each PDF's
    # account suffix and holder. This is not persisted.
    accounts_for_transfer_matcher = {
        PRIMARY_ACCOUNT_ID: {
            "account_id": PRIMARY_ACCOUNT_ID,
            "user_id": TEST_USER_ID,
            "verified": True,
            "masked_account_number": "XXXX XXXX 4821",
        },
        SECONDARY_ACCOUNT_ID: {
            "account_id": SECONDARY_ACCOUNT_ID,
            "user_id": TEST_USER_ID,
            "verified": True,
            "masked_account_number": "XXXX XXXX 7392",
        },
    }

    all_transactions = []
    next_transaction_id = 100001
    for statement in (primary, secondary):
        for transaction in statement["transactions"]:
            transaction["transaction_id"] = next_transaction_id
            next_transaction_id += 1
            all_transactions.append(transaction)

    print("\n" + "=" * 70)
    print("PDF-DERIVED INTERNAL TRANSFER RECONCILIATION")
    print("=" * 70)

    transfer_result = reconcile_internal_transfers(
        all_transactions,
        accounts_for_transfer_matcher,
        max_date_gap_days=1,
    )
    print(json.dumps(transfer_result, indent=2, default=str))

    # Existing matcher must explicitly report read-only operation.
    require(
        transfer_result.get("writes_performed") is False,
        "Internal transfer matcher did not confirm read-only mode.",
    )

    print("\n" + "=" * 70)
    print("PDF-DERIVED MULTI-ACCOUNT CONSOLIDATION")
    print("=" * 70)

    # Important: pass the actual records generated from both PDFs.
    # No manually constructed transaction dictionaries are supplied here.
    multi_result = reconcile_multiple_accounts(
        all_transactions,
        accounts=[
            {
                "account_id": PRIMARY_ACCOUNT_ID,
                "account_name": "Primary Account",
                "institution_name": "Meridian Crest Bank",
                "currency": "INR",
            },
            {
                "account_id": SECONDARY_ACCOUNT_ID,
                "account_name": "Secondary Account",
                "institution_name": "Meridian Crest Bank",
                "currency": "INR",
            },
        ],
        date_tolerance_days=1,
    )

    print("\nMULTI-ACCOUNT SUMMARY")
    print(json.dumps(multi_result["summary"], indent=2, default=str))

    print("\nACCOUNT REPORTS")
    print(json.dumps(multi_result["account_reports"], indent=2, default=str))

    print("\nCONSOLIDATED REPORT")
    print(json.dumps(multi_result["consolidated_report"], indent=2, default=str))

    print("\nPDF-DERIVED TRANSFER MATCHES")
    print(json.dumps(
        multi_result["transfer_reconciliation"]["matches"],
        indent=2,
        default=str,
    ))

    # Assertions compare PDF-derived results with independent statement totals.
    require(multi_result.get("success") is True, "Multi-account reconciliation failed")
    summary = multi_result["summary"]
    require(summary["total_accounts"] == 2, f"Expected 2 accounts, got {summary['total_accounts']}")
    require(summary["total_transactions"] == 19,
            f"Expected 19 PDF-derived transactions, got {summary['total_transactions']}")
    require(summary["matched_internal_transfer_pairs"] == 1,
            f"Expected 1 internal transfer pair, got {summary['matched_internal_transfer_pairs']}")
    require(summary["unmatched_transfer_candidates"] == 0,
            f"Unexpected ambiguous transfer candidates: {summary['unmatched_transfer_candidates']}")

    consolidated = multi_result["consolidated_report"]["INR"]
    for key, expected_value in EXPECTED_CONSOLIDATED.items():
        actual_value = consolidated.get(key)
        require(
            actual_value == expected_value,
            f"Consolidated {key} mismatch: expected {expected_value}, got {actual_value}",
        )

    # Verify per-account results and running-balance-derived values.
    reports = {row["account_id"]: row for row in multi_result["account_reports"]}
    expected_account_ids = {
        PRIMARY_ACCOUNT_ID: "primary",
        SECONDARY_ACCOUNT_ID: "secondary",
    }
    for account_id, label in expected_account_ids.items():
        report = reports[account_id]
        expected = EXPECTED[label]
        for key in (
            "transaction_count",
            "external_income",
            "external_expenses",
            "internal_transfer_debits",
            "internal_transfer_credits",
            "opening_balance_estimate",
            "closing_balance",
        ):
            require(
                report.get(key) == expected[key],
                f"{label} account {key} mismatch: expected {expected[key]}, got {report.get(key)}",
            )

    matches = multi_result["transfer_reconciliation"]["matches"]
    require(len(matches) == 1, f"Expected exactly one transfer match, got {len(matches)}")
    matched_transfer = matches[0]
    require(float(matched_transfer["amount"]) == 5000.00,
            f"Expected transfer amount 5000.00, got {matched_transfer.get('amount')}")
    require(str(matched_transfer["debit_transaction"]["account_id"]) == str(PRIMARY_ACCOUNT_ID),
            "Transfer debit did not originate from primary account")
    require(str(matched_transfer["credit_transaction"]["account_id"]) == str(SECONDARY_ACCOUNT_ID),
            "Transfer credit did not arrive in secondary account")

    print("\n" + "=" * 70)
    print("ALL PDF-DRIVEN NOVEMBER INTEGRATION ASSERTIONS PASSED")
    print("=" * 70)
    print("PDFs processed: 2")
    print("Transactions parsed and validated: 19")
    print("Internal transfer pairs matched: 1")
    print("External income: INR 49,650.00")
    print("External expenses: INR 13,749.00")
    print("Net external cash flow: INR 35,901.00")
    print("Consolidated closing balance: INR 105,901.00")
    print("Writes performed: False")
    print("MySQL writes: 0")
    print("ChromaDB writes: 0")


if __name__ == "__main__":
    main()
