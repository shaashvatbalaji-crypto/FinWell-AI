"""
FinWell AI — Standalone November + December 2026 PDF integration test.

Run ONLY this file from the FinWell_AI project root:
    python .\run_all_pdf_integration_tests.py

This file contains the test runner and test logic for BOTH months.
It does NOT import either of the old test scripts from the tests folder.

It DOES import the existing FinWell AI application modules for PDF extraction,
preprocessing, validation, internal-transfer matching, and multi-account
reconciliation. Transactions are always derived from the four PDFs below;
no transaction rows are hardcoded.

Safety:
- No MySQL writes
- No ChromaDB writes
- No transaction storage
- No reconciliation case creation
- Temporary user/account/transaction IDs are in-memory only
"""

import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Existing FinWell AI application modules (not test scripts).
from pdf_extraction.pdf_validator import validate_pdf
from pdf_extraction.pdf_reader import extract_pdf_text
from pdf_extraction.document_classifier import classify_document

from preprocessing.text_cleaner import clean_extracted_text
from preprocessing.transaction_parser import parse_transactions
from preprocessing.data_normalizer import normalize_transactions
from preprocessing.data_validator import validate_transactions

from reconciliation.internal_transfer_matcher import reconcile_internal_transfers
from reconciliation.multi_account_reconciler import reconcile_multiple_accounts


DOWNLOADS = Path.home() / "Downloads"

PERIODS = [
    {
        "name": "NOVEMBER 2026",
        "primary_pdf": DOWNLOADS / "finwell_reconciliation_primary_nov2026.pdf",
        "secondary_pdf": DOWNLOADS / "finwell_reconciliation_secondary_nov2026.pdf",
        "user_id": 9001,
        "primary_account_id": 9101,
        "secondary_account_id": 9102,
        "expected": {
            "primary": {
                "account_suffix": "4821",
                "transaction_count": 14,
                "total_debit": 15799.00,
                "total_credit": 41650.00,
                "external_income": 41650.00,
                "external_expenses": 10799.00,
                "internal_transfer_debits": 5000.00,
                "internal_transfer_credits": 0.00,
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
                "opening_balance_estimate": 20000.00,
                "closing_balance": 30050.00,
            },
        },
        "expected_consolidated": {
            "external_income": 49650.00,
            "external_expenses": 13749.00,
            "net_external_cash_flow": 35901.00,
            "internal_transfer_debits": 5000.00,
            "internal_transfer_credits": 5000.00,
            "opening_balance_estimate": 70000.00,
            "closing_balance": 105901.00,
        },
        "expected_transfer_references": {"TRF501"},
        "expected_transactions": 19,
        "expected_transfer_pairs": 1,
    },
    {
        "name": "DECEMBER 2026",
        "primary_pdf": DOWNLOADS / "finwell_reconciliation_complex_dec2026.pdf",
        "secondary_pdf": DOWNLOADS / "finwell_reconciliation_secondary_complex_dec2026.pdf",
        "user_id": 9002,
        "primary_account_id": 9201,
        "secondary_account_id": 9202,
        "expected": {
            "primary": {
                "account_suffix": "4821",
                "transaction_count": 39,
                "total_debit": 124029.60,
                "total_credit": 80360.00,
                "external_income": 76360.00,
                "external_expenses": 102029.60,
                "internal_transfer_debits": 22000.00,
                "internal_transfer_credits": 4000.00,
                "opening_balance_estimate": 75851.00,
                "closing_balance": 32181.40,
            },
            "secondary": {
                "account_suffix": "7392",
                "transaction_count": 13,
                "total_debit": 12666.70,
                "total_credit": 34095.00,
                "external_income": 12095.00,
                "external_expenses": 8666.70,
                "internal_transfer_debits": 4000.00,
                "internal_transfer_credits": 22000.00,
                "opening_balance_estimate": 30050.00,
                "closing_balance": 51478.30,
            },
        },
        "expected_consolidated": {
            "external_income": 88455.00,
            "external_expenses": 110696.30,
            "net_external_cash_flow": -22241.30,
            "internal_transfer_debits": 26000.00,
            "internal_transfer_credits": 26000.00,
            "opening_balance_estimate": 105901.00,
            "closing_balance": 83659.70,
        },
        "expected_transfer_references": {"TRF601", "TRF602", "TRF603", "TRF604"},
        "expected_transactions": 52,
        "expected_transfer_pairs": 4,
    },
]


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def money(value):
    return round(float(value or 0), 2)


def process_pdf(period, label, pdf_path, account_id):
    expected = period["expected"][label]

    print("\n" + "=" * 78)
    print(f"{period['name']} — PROCESSING {label.upper()} PDF: {pdf_path.name}")
    print("=" * 78)

    require(pdf_path.is_file(), f"Statement PDF not found: {pdf_path}")

    pdf_check = validate_pdf(str(pdf_path))
    print("\n[1] PDF VALIDATION")
    print(json.dumps(pdf_check, indent=2, default=str))
    require(pdf_check.get("valid") is True, f"PDF validation failed: {pdf_path}")

    extraction = extract_pdf_text(str(pdf_path))
    require(
        extraction.get("success") is True,
        extraction.get("error", f"PDF extraction failed: {pdf_path}"),
    )
    extracted_text = extraction.get("full_text", "")
    require(bool(extracted_text.strip()), f"No selectable text in {pdf_path}")

    digits = re.sub(r"\D", "", extracted_text)
    require(
        expected["account_suffix"] in digits,
        f"Expected account suffix {expected['account_suffix']} not found in {pdf_path.name}",
    )
    require(
        "ARJUN KUMAR" in extracted_text.upper(),
        f"Expected account holder ARJUN KUMAR not found in {pdf_path.name}",
    )

    cleaning = clean_extracted_text(extracted_text)
    require(
        isinstance(cleaning, dict) and cleaning.get("success") is True,
        cleaning.get("error", "Text cleaning failed")
        if isinstance(cleaning, dict)
        else "Unexpected text-cleaner response",
    )
    cleaned_text = cleaning.get("cleaned_text", "")
    require(bool(cleaned_text.strip()), "Text cleaner returned empty text")

    classification = classify_document(cleaned_text)
    require(
        classification.get("success") is True,
        classification.get("error", "Document classification failed"),
    )
    require(
        classification.get("document_type") == "bank_statement",
        f"Unexpected document type: {classification.get('document_type')}",
    )

    parsing = parse_transactions(cleaned_text)
    require(
        parsing.get("success") is True,
        parsing.get("error", "Transaction parsing failed"),
    )
    parsed = parsing.get("transactions", [])

    normalization = normalize_transactions(parsed)
    require(
        normalization.get("success") is True,
        normalization.get("error", "Transaction normalization failed"),
    )
    normalized = normalization.get("transactions", [])

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

    require(
        invalid_count == 0 and not invalid,
        "Invalid transactions found; refusing to reconcile an incomplete statement:\n"
        + json.dumps(invalid, indent=2, default=str),
    )

    enriched = []
    for index, transaction in enumerate(valid, start=1):
        item = dict(transaction)
        item["transaction_id"] = None
        item["user_id"] = period["user_id"]
        item["account_id"] = account_id
        item["currency"] = str(item.get("currency") or "INR").upper()

        if not item.get("date"):
            item["date"] = item.get("transaction_date")

        require(item.get("date") is not None, f"Missing date in {label} row {index}")
        require(
            item.get("balance") is not None,
            f"Missing running balance in {label} row {index}; cannot verify consolidation.",
        )
        enriched.append(item)

    total_debit = money(sum(money(row.get("debit")) for row in enriched))
    total_credit = money(sum(money(row.get("credit")) for row in enriched))

    print("\n[3] VALIDATED PDF-DERIVED TRANSACTIONS")
    for index, row in enumerate(enriched, start=1):
        print(
            f"{index:02d}. Date={row.get('date')} | "
            f"Description={row.get('description')} | "
            f"Debit={row.get('debit')} | Credit={row.get('credit')} | "
            f"Balance={row.get('balance')}"
        )

    require(
        len(enriched) == expected["transaction_count"],
        f"{label}: expected {expected['transaction_count']} transactions, got {len(enriched)}",
    )
    require(
        total_debit == expected["total_debit"],
        f"{label}: debit mismatch: expected {expected['total_debit']}, got {total_debit}",
    )
    require(
        total_credit == expected["total_credit"],
        f"{label}: credit mismatch: expected {expected['total_credit']}, got {total_credit}",
    )

    return {
        "transactions": enriched,
        "total_debit": total_debit,
        "total_credit": total_credit,
    }


def run_period(period):
    print("\n\n" + "#" * 78)
    print(f"STARTING {period['name']} PDF INTEGRATION TEST")
    print("#" * 78)

    primary_id = period["primary_account_id"]
    secondary_id = period["secondary_account_id"]
    user_id = period["user_id"]

    primary = process_pdf(period, "primary", period["primary_pdf"], primary_id)
    secondary = process_pdf(period, "secondary", period["secondary_pdf"], secondary_id)

    account_metadata = {
        primary_id: {
            "account_id": primary_id,
            "user_id": user_id,
            "verified": True,
            "masked_account_number": "XXXX XXXX 4821",
        },
        secondary_id: {
            "account_id": secondary_id,
            "user_id": user_id,
            "verified": True,
            "masked_account_number": "XXXX XXXX 7392",
        },
    }

    all_transactions = []
    next_id = user_id * 100000
    for statement in (primary, secondary):
        for transaction in statement["transactions"]:
            transaction["transaction_id"] = next_id
            next_id += 1
            all_transactions.append(transaction)

    print("\n[4] INTERNAL TRANSFER RECONCILIATION — DRY RUN")
    transfer_result = reconcile_internal_transfers(
        all_transactions,
        account_metadata,
        max_date_gap_days=1,
    )
    print(json.dumps(transfer_result, indent=2, default=str))

    require(transfer_result.get("success") is True, "Internal transfer reconciliation failed")
    require(
        transfer_result.get("writes_performed") is False,
        "Transfer matcher did not confirm read-only mode.",
    )
    require(
        transfer_result.get("candidate_count") == period["expected_transfer_pairs"],
        f"Expected {period['expected_transfer_pairs']} transfer candidates, "
        f"got {transfer_result.get('candidate_count')}",
    )

    candidate_refs = {
        str(row.get("reference")) for row in transfer_result.get("candidates", [])
    }
    require(
        candidate_refs == period["expected_transfer_references"],
        f"Transfer candidate references mismatch: expected "
        f"{sorted(period['expected_transfer_references'])}, got {sorted(candidate_refs)}",
    )

    print("\n[5] MULTI-ACCOUNT CONSOLIDATION")
    multi_result = reconcile_multiple_accounts(
        all_transactions,
        accounts=[
            {
                "account_id": primary_id,
                "account_name": "Primary Account",
                "institution_name": "Meridian Crest Bank",
                "currency": "INR",
            },
            {
                "account_id": secondary_id,
                "account_name": "Secondary Account",
                "institution_name": "Meridian Crest Bank",
                "currency": "INR",
            },
        ],
        date_tolerance_days=1,
    )

    print("\nMULTI-ACCOUNT SUMMARY")
    print(json.dumps(multi_result.get("summary"), indent=2, default=str))
    print("\nACCOUNT REPORTS")
    print(json.dumps(multi_result.get("account_reports"), indent=2, default=str))
    print("\nCONSOLIDATED REPORT")
    print(json.dumps(multi_result.get("consolidated_report"), indent=2, default=str))
    print("\nPDF-DERIVED TRANSFER MATCHES")
    print(json.dumps(
        multi_result.get("transfer_reconciliation", {}).get("matches", []),
        indent=2,
        default=str,
    ))

    require(multi_result.get("success") is True, "Multi-account reconciliation failed")
    summary = multi_result["summary"]
    require(summary["total_accounts"] == 2, f"Expected 2 accounts, got {summary['total_accounts']}")
    require(
        summary["total_transactions"] == period["expected_transactions"],
        f"Expected {period['expected_transactions']} PDF-derived transactions, "
        f"got {summary['total_transactions']}",
    )
    require(
        summary["matched_internal_transfer_pairs"] == period["expected_transfer_pairs"],
        f"Expected {period['expected_transfer_pairs']} matched transfer pairs, "
        f"got {summary['matched_internal_transfer_pairs']}",
    )
    require(
        summary["unmatched_transfer_candidates"] == 0,
        f"Unexpected ambiguous transfer candidates: {summary['unmatched_transfer_candidates']}",
    )

    consolidated = multi_result["consolidated_report"]["INR"]
    for key, expected_value in period["expected_consolidated"].items():
        actual_value = money(consolidated.get(key))
        require(
            actual_value == expected_value,
            f"Consolidated {key} mismatch: expected {expected_value}, got {actual_value}",
        )

    reports = {row["account_id"]: row for row in multi_result["account_reports"]}
    for account_id, label in ((primary_id, "primary"), (secondary_id, "secondary")):
        report = reports[account_id]
        expected = period["expected"][label]
        for key in (
            "transaction_count",
            "external_income",
            "external_expenses",
            "internal_transfer_debits",
            "internal_transfer_credits",
            "opening_balance_estimate",
            "closing_balance",
        ):
            actual = report.get(key)
            expected_value = expected[key]
            if key == "transaction_count":
                passed = actual == expected_value
            else:
                passed = money(actual) == expected_value
            require(
                passed,
                f"{label} account {key} mismatch: expected {expected_value}, got {actual}",
            )

    matches = multi_result["transfer_reconciliation"]["matches"]
    require(
        len(matches) == period["expected_transfer_pairs"],
        f"Expected {period['expected_transfer_pairs']} transfer matches, got {len(matches)}",
    )
    matched_refs = {str(match.get("reference")) for match in matches}
    require(
        matched_refs == period["expected_transfer_references"],
        f"Multi-account transfer references mismatch: {sorted(matched_refs)}",
    )

    print("\n" + "=" * 78)
    print(f"{period['name']} — ALL INTEGRATION ASSERTIONS PASSED")
    print("=" * 78)
    print(f"PDFs processed: 2")
    print(f"Transactions parsed and validated: {period['expected_transactions']}")
    print(f"Internal transfer pairs matched: {period['expected_transfer_pairs']}")
    for key, value in period["expected_consolidated"].items():
        print(f"{key}: INR {value:,.2f}")
    print("Writes performed: False")
    print("MySQL writes: 0")
    print("ChromaDB writes: 0")


def main():
    results = []

    print("=" * 78)
    print("FINWELL AI — STANDALONE NOVEMBER + DECEMBER PDF INTEGRATION TEST")
    print("This runner contains both test flows; no separate test scripts are imported.")
    print("=" * 78)

    for period in PERIODS:
        try:
            run_period(period)
            results.append((period["name"], True, None))
        except Exception as exc:
            results.append((period["name"], False, str(exc)))
            print(f"\n{period['name']} TEST FAILED: {exc}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 78)
    print("FINAL COMBINED TEST SUMMARY")
    print("=" * 78)
    for name, passed, error in results:
        print(f"{name}: {'PASSED' if passed else 'FAILED — ' + error}")

    passed_count = sum(1 for _, passed, _ in results if passed)
    failed_count = len(results) - passed_count
    print(f"Passed: {passed_count}/{len(results)}")
    print(f"Failed: {failed_count}/{len(results)}")

    if failed_count:
        raise SystemExit(1)

    print("\nBOTH MONTHS PASSED ALL PDF-DRIVEN INTEGRATION ASSERTIONS.")


if __name__ == "__main__":
    main()
