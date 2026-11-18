
"""
FinWell AI - November 2026 Full Reconciliation Integration Test

Purpose:
1. Extract and preprocess both synthetic bank statement PDFs.
2. Run all five reconciliation engines through the unified coordinator.
3. Validate duplicate, internal-transfer, refund and settlement results.
4. Reconcile consolidated and individual statement balances.
5. Verify original input transactions remain unchanged.

Safety:
- No MySQL writes.
- No ChromaDB writes.
- No production ingestion service.
- No original transaction modification.
- Gateway and settlement data are synthetic and in-memory only.
"""

import sys
import json
import copy
from pathlib import Path
from decimal import Decimal

# ============================================================
# 1. PROJECT PATH AND IMPORTS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pdf_extraction.pdf_validator import validate_pdf
from pdf_extraction.pdf_reader import extract_pdf_text

from preprocessing.text_cleaner import clean_extracted_text
from preprocessing.transaction_parser import parse_transactions
from preprocessing.data_normalizer import normalize_transactions
from preprocessing.data_validator import validate_transactions

from reconciliation.unified_reconciliation_service import (
    reconcile_all_transactions,
)

from reconciliation.balance_reconciler import (
    reconcile_statement_balance,
)


# ============================================================
# 2. TEST CONFIGURATION
# ============================================================

PRIMARY_PDF = Path(
    r"C:\Users\shaas\Downloads\finwell_reconciliation_primary_nov2026.pdf"
)

SECONDARY_PDF = Path(
    r"C:\Users\shaas\Downloads\finwell_reconciliation_secondary_nov2026.pdf"
)

# Synthetic identity used only inside this in-memory test.
# It is NOT a real MySQL user or account ID.
TEST_USER_ID = 900001

PRIMARY_ACCOUNT_ID = 4821
SECONDARY_ACCOUNT_ID = 7392

PRIMARY_OPENING_BALANCE = Decimal("50000.00")
PRIMARY_CLOSING_BALANCE = Decimal("75851.00")

SECONDARY_OPENING_BALANCE = Decimal("20000.00")
SECONDARY_CLOSING_BALANCE = Decimal("30050.00")

CURRENCY = "INR"

# Verified ownership is supplied only as test metadata.
# No database account ownership is being asserted or changed.
TEST_ACCOUNTS = {
    PRIMARY_ACCOUNT_ID: {
        "account_id": PRIMARY_ACCOUNT_ID,
        "user_id": TEST_USER_ID,
        "verified": True,
        "currency": CURRENCY,
    },
    SECONDARY_ACCOUNT_ID: {
        "account_id": SECONDARY_ACCOUNT_ID,
        "user_id": TEST_USER_ID,
        "verified": True,
        "currency": CURRENCY,
    },
}


# ============================================================
# 3. SYNTHETIC SETTLEMENT TEST DATA
# ============================================================

# Two gateway payments belonging to one settlement batch.
# Gross: 3000 + 2000 = 5000
# Fees:    60 +   40 =  100
# Net:                  4900

GATEWAY_TRANSACTIONS = [
    {
        "transaction_id": 92001,
        "user_id": TEST_USER_ID,
        "date": "2026-11-10",
        "description": "Gateway payment A",
        "gross_amount": Decimal("3000.00"),
        "processing_fee": Decimal("60.00"),
        "currency": CURRENCY,
        "settlement_reference": "SETTLE_TEST_501",
    },
    {
        "transaction_id": 92002,
        "user_id": TEST_USER_ID,
        "date": "2026-11-10",
        "description": "Gateway payment B",
        "gross_amount": Decimal("2000.00"),
        "processing_fee": Decimal("40.00"),
        "currency": CURRENCY,
        "settlement_reference": "SETTLE_TEST_501",
    },
]

# One correct bank settlement and one unrelated bank credit.
# The unrelated credit must not be matched.

BANK_SETTLEMENT_TRANSACTIONS = [
    {
        "transaction_id": 93001,
        "user_id": TEST_USER_ID,
        "date": "2026-11-11",
        "description": "Gateway settlement",
        "credit": Decimal("4900.00"),
        "currency": CURRENCY,
        "reference": "SETTLE_TEST_501",
    },
    {
        "transaction_id": 93002,
        "user_id": TEST_USER_ID,
        "date": "2026-11-11",
        "description": "Unrelated settlement",
        "credit": Decimal("4900.00"),
        "currency": CURRENCY,
        "reference": "WRONG_REFERENCE",
    },
]


# ============================================================
# 4. CONSOLIDATED BALANCE CONFIGURATION
# ============================================================

# Both accounts are included in all_transactions.
# Their running balances must NOT be checked as one sequence.
#
# Instead:
# - Coordinator checks the consolidated opening/closing balance.
# - Individual account checks validate each running balance below.

CONSOLIDATED_OPENING_BALANCE = (
    PRIMARY_OPENING_BALANCE + SECONDARY_OPENING_BALANCE
)

CONSOLIDATED_CLOSING_BALANCE = (
    PRIMARY_CLOSING_BALANCE + SECONDARY_CLOSING_BALANCE
)

# Expected:
# Opening: 70000.00
# Closing: 105901.00
# Difference: 0.00


# ============================================================
# 5. DISPLAY HELPERS
# ============================================================

def heading(message):
    print("\n" + "=" * 75)
    print(message)
    print("=" * 75)


def print_json(data):
    print(
        json.dumps(
            data,
            indent=2,
            default=str,
            ensure_ascii=False,
        )
    )


def money(value):
    return Decimal(str(value or 0)).quantize(
        Decimal("0.01")
    )


# ============================================================
# 6. CLEANER OUTPUT ADAPTER
# ============================================================

def get_cleaned_text(result):

    if isinstance(result, str):
        return result

    if isinstance(result, dict):

        if result.get("success") is False:
            raise RuntimeError(
                result.get("error", "Text cleaning failed.")
            )

        for key in (
            "cleaned_text",
            "clean_text",
            "text",
            "content",
            "full_text",
            "extracted_text",
        ):
            value = result.get(key)

            if isinstance(value, str):
                return value

    if isinstance(result, (tuple, list)):

        for value in result:
            if isinstance(value, str):
                return value

    raise TypeError(
        "Could not extract cleaned text from cleaner result."
    )


# ============================================================
# 7. PROCESS ONE PDF
# ============================================================

def process_statement(pdf_path, account_id, first_transaction_id):

    heading(f"PROCESSING PDF: {pdf_path.name}")

    if not pdf_path.exists():
        raise FileNotFoundError(
            f"PDF not found: {pdf_path}"
        )

    # --------------------------------------------------------
    # PDF validation
    # --------------------------------------------------------

    validation = validate_pdf(str(pdf_path))

    print("PDF validation:")
    print_json(validation)

    if not validation.get("valid"):
        raise RuntimeError(
            validation.get("error", "PDF validation failed.")
        )

    # --------------------------------------------------------
    # PDF text extraction
    # --------------------------------------------------------

    extraction = extract_pdf_text(str(pdf_path))

    if not extraction.get("success"):
        raise RuntimeError(
            extraction.get("error", "PDF extraction failed.")
        )

    raw_text = extraction.get("full_text")

    if not isinstance(raw_text, str) or not raw_text.strip():
        raise RuntimeError(
            "No selectable PDF text was extracted."
        )

    # --------------------------------------------------------
    # Existing FinWell text cleaner
    # --------------------------------------------------------

    cleaner_result = clean_extracted_text(raw_text)
    cleaned_text = get_cleaned_text(cleaner_result)

    if not cleaned_text.strip():
        raise RuntimeError(
            "No text remained after cleaning."
        )

    # --------------------------------------------------------
    # Existing transaction parser
    # --------------------------------------------------------

    parsed = parse_transactions(cleaned_text)

    if not parsed.get("success"):
        raise RuntimeError(
            parsed.get("error", "Transaction parsing failed.")
        )

    parsed_transactions = parsed.get("transactions", [])

    # --------------------------------------------------------
    # Existing transaction normalizer
    # --------------------------------------------------------

    normalized_result = normalize_transactions(
        parsed_transactions
    )

    if not normalized_result.get("success"):
        raise RuntimeError(
            normalized_result.get(
                "error",
                "Transaction normalization failed.",
            )
        )

    normalized_transactions = normalized_result.get(
        "transactions", []
    )

    # --------------------------------------------------------
    # Existing transaction validator
    # --------------------------------------------------------

    validation_result = validate_transactions(
        normalized_transactions
    )

    if not validation_result.get("success"):
        raise RuntimeError(
            validation_result.get(
                "error",
                "Transaction validation failed.",
            )
        )

    valid_transactions = validation_result.get(
        "valid_transactions", []
    )

    invalid_count = validation_result.get(
        "invalid_count", 0
    )

    print("\nDOCUMENT PROCESSING SUMMARY")
    print(f"Document: {pdf_path.name}")
    print(f"Account: {account_id}")
    print(f"Pages: {validation.get('total_pages')}")
    print(f"Parsed transactions: {len(parsed_transactions)}")
    print(f"Normalized transactions: {len(normalized_transactions)}")
    print(f"Valid transactions: {len(valid_transactions)}")
    print(f"Invalid transactions: {invalid_count}")

    if invalid_count:
        raise AssertionError(
            f"{pdf_path.name} contains {invalid_count} invalid transactions."
        )

    if len(valid_transactions) != len(parsed_transactions):
        raise AssertionError(
            "Parsed and valid transaction counts do not match."
        )

    # --------------------------------------------------------
    # Attach test-only metadata.
    # Original parser and normalizer outputs are not modified.
    # --------------------------------------------------------

    enriched_transactions = []

    for index, item in enumerate(valid_transactions):

        tx = dict(item)

        tx["transaction_id"] = (
            first_transaction_id + index
        )

        tx["user_id"] = TEST_USER_ID
        tx["account_id"] = account_id
        tx["currency"] = CURRENCY

        # Preserve the date key and add transaction_date
        # for compatibility with reconciliation engines.

        if not tx.get("date") and tx.get("transaction_date"):
            tx["date"] = tx["transaction_date"]

        if not tx.get("transaction_date") and tx.get("date"):
            tx["transaction_date"] = tx["date"]

        tx["debit"] = money(tx.get("debit"))
        tx["credit"] = money(tx.get("credit"))

        enriched_transactions.append(tx)

    return {
        "transactions": enriched_transactions,
        "parsed_count": len(parsed_transactions),
        "valid_count": len(valid_transactions),
        "invalid_count": invalid_count,
        "page_count": validation.get("total_pages"),
    }


# ============================================================
# 8. COMPACT ENGINE OUTPUT
# ============================================================

def print_engine_results(unified_result):

    engines = unified_result.get("engines", {})

    heading("UNIFIED RECONCILIATION ENGINE SUMMARY")

    print("Available engines:", list(engines.keys()))

    for engine_name, engine_result in engines.items():

        heading(engine_name.upper())

        if not isinstance(engine_result, dict):
            print(engine_result)
            continue

        if engine_name == "duplicates":

            # Avoid printing all pairwise comparisons.

            compact = {
                key: value
                for key, value in engine_result.items()
                if key not in ("comparisons",)
            }

            print_json(compact)

            comparisons = engine_result.get("comparisons", [])

            candidate_comparisons = [
                item
                for item in comparisons
                if (
                    isinstance(item, dict)
                    and isinstance(item.get("result"), dict)
                    and item["result"].get("is_candidate") is True
                )
            ]

            if candidate_comparisons:
                print("\nDuplicate candidate details:")
                print_json(candidate_comparisons)

        else:
            print_json(engine_result)


# ============================================================
# 9. INDIVIDUAL BALANCE RECONCILIATION
# ============================================================

def run_balance_check(
    account_name,
    transactions,
    opening_balance,
    closing_balance,
):

    heading(f"{account_name} BALANCE RECONCILIATION")

    result = reconcile_statement_balance(
        transactions=transactions,
        opening_balance=opening_balance,
        closing_balance=closing_balance,
        tolerance=Decimal("0.01"),
        check_running_balance=True,
    )

    print_json(result)

    if not result.get("success"):
        raise AssertionError(
            f"{account_name}: balance reconciler returned failure."
        )

    if not result.get("statement_balanced"):
        raise AssertionError(
            f"{account_name}: statement balance did not reconcile."
        )

    if result.get("running_balance_mismatches"):
        raise AssertionError(
            f"{account_name}: running balance mismatches found."
        )

    if result.get("writes_performed") is not False:
        raise AssertionError(
            f"{account_name}: unexpected write operation."
        )

    return result


# ============================================================
# 10. FIVE-ENGINE REGRESSION ASSERTIONS
# ============================================================

def validate_all_engines(unified_result):

    heading("FIVE-ENGINE REGRESSION VALIDATION")

    engines = unified_result.get("engines", {})

    required_engines = [
        "duplicates",
        "internal_transfers",
        "refunds",
        "settlements",
        "balance",
    ]

    # --------------------------------------------------------
    # Verify every engine exists and actually executed.
    # --------------------------------------------------------

    for engine_name in required_engines:

        if engine_name not in engines:
            raise AssertionError(
                f"Missing reconciliation engine: {engine_name}"
            )

        engine_result = engines[engine_name]

        if not isinstance(engine_result, dict):
            raise AssertionError(
                f"Invalid result from {engine_name} engine."
            )

        if engine_result.get("success") is not True:
            raise AssertionError(
                f"{engine_name} engine failed: {engine_result}"
            )

        if engine_result.get("status") == "skipped":
            raise AssertionError(
                f"{engine_name} engine was skipped."
            )

        print(f"PASS: {engine_name}")

    # --------------------------------------------------------
    # Settlement matching validation
    # --------------------------------------------------------

    settlement_result = engines["settlements"]

    if settlement_result.get("candidate_count") != 1:
        raise AssertionError(
            "Expected exactly one settlement candidate."
        )

    candidates = settlement_result.get(
        "matched_candidates", []
    )

    if len(candidates) != 1:
        raise AssertionError(
            "Expected exactly one matched settlement candidate."
        )

    candidate = candidates[0]

    if candidate.get("status") != "proposed":
        raise AssertionError(
            "Settlement candidate must remain proposed."
        )

    if candidate.get("gross_amount") != Decimal("5000.00"):
        raise AssertionError(
            "Incorrect settlement gross amount."
        )

    if candidate.get("processing_fee") != Decimal("100.00"):
        raise AssertionError(
            "Incorrect settlement processing fee."
        )

    if candidate.get("expected_net") != Decimal("4900.00"):
        raise AssertionError(
            "Incorrect expected settlement net amount."
        )

    if len(candidate.get("gateway_transaction_ids", [])) != 2:
        raise AssertionError(
            "Expected both gateway transactions in the settlement."
        )

    if settlement_result.get("invalid_transactions"):
        raise AssertionError(
            "Settlement engine reported invalid transactions."
        )

    if settlement_result.get("review_required"):
        raise AssertionError(
            "Unexpected settlement review candidates."
        )

    unmatched_bank = settlement_result.get(
        "unmatched_bank", []
    )

    if len(unmatched_bank) != 1:
        raise AssertionError(
            "Expected the unrelated bank settlement to remain unmatched."
        )

    unmatched_ids = {
        item.get("transaction_id")
        for item in unmatched_bank
        if isinstance(item, dict)
    }

    if 93002 not in unmatched_ids:
        raise AssertionError(
            "The bank transaction with the wrong reference "
            "was not correctly left unmatched."
        )

    print("PASS: Settlement grouping")
    print("PASS: Settlement fee calculation")
    print("PASS: Settlement reference validation")
    print("PASS: Unrelated bank credit remains unmatched")

    # --------------------------------------------------------
    # Consolidated balance validation
    # --------------------------------------------------------

    balance_result = engines["balance"]

    if balance_result.get("statement_balanced") is not True:
        raise AssertionError(
            "Consolidated balance reconciliation failed."
        )

    if money(balance_result.get("difference")) != Decimal("0.00"):
        raise AssertionError(
            "Consolidated balance difference is not zero."
        )

    if balance_result.get("invalid_transaction_count") != 0:
        raise AssertionError(
            "Consolidated balance engine reported invalid transactions."
        )

    if money(balance_result.get("opening_balance")) != (
        CONSOLIDATED_OPENING_BALANCE
    ):
        raise AssertionError(
            "Incorrect consolidated opening balance."
        )

    if money(balance_result.get("actual_closing_balance")) != (
        CONSOLIDATED_CLOSING_BALANCE
    ):
        raise AssertionError(
            "Incorrect consolidated closing balance."
        )

    if balance_result.get("running_balance_checked") is not False:
        raise AssertionError(
            "Combined account sequence should not run an individual "
            "running-balance check."
        )

    print("PASS: Consolidated opening and closing balances")
    print("PASS: Consolidated balance difference is zero")

    # --------------------------------------------------------
    # Read-only guarantees
    # --------------------------------------------------------

    if unified_result.get("writes_performed") is not False:
        raise AssertionError(
            "Unified coordinator reported unexpected writes."
        )

    if unified_result.get("original_transactions_modified") is not False:
        raise AssertionError(
            "Unified coordinator reported input modification."
        )

    if settlement_result.get("writes_performed") is not False:
        raise AssertionError(
            "Settlement engine reported unexpected writes."
        )

    print("PASS: No database or ChromaDB writes reported")

    return {
        "all_five_engines_executed": True,
        "settlement_candidate_count": 1,
        "settlement_status": "proposed",
        "settlement_gross": "5000.00",
        "settlement_fees": "100.00",
        "settlement_net": "4900.00",
        "consolidated_balance_difference": "0.00",
        "read_only": True,
    }


# ============================================================
# 11. MAIN INTEGRATION TEST
# ============================================================

def main():

    heading("FINWELL AI - NOVEMBER 2026 FULL RECONCILIATION TEST")

    print("Execution mode: Real engines, in-memory dry run")
    print("MySQL writes: DISABLED")
    print("ChromaDB writes: DISABLED")
    print("Production ingestion service: NOT USED")
    print("Synthetic settlement data: ENABLED")

    # --------------------------------------------------------
    # Process both statements
    # --------------------------------------------------------

    primary_result = process_statement(
        PRIMARY_PDF,
        PRIMARY_ACCOUNT_ID,
        first_transaction_id=100001,
    )

    secondary_result = process_statement(
        SECONDARY_PDF,
        SECONDARY_ACCOUNT_ID,
        first_transaction_id=200001,
    )

    primary_transactions = primary_result["transactions"]
    secondary_transactions = secondary_result["transactions"]

    all_transactions = (
        primary_transactions + secondary_transactions
    )

    print("\nTRANSACTION INPUT SUMMARY")
    print(f"Primary account: {len(primary_transactions)}")
    print(f"Secondary account: {len(secondary_transactions)}")
    print(f"Total: {len(all_transactions)}")

    if len(primary_transactions) != 14:
        raise AssertionError(
            "Expected 14 primary account transactions."
        )

    if len(secondary_transactions) != 5:
        raise AssertionError(
            "Expected 5 secondary account transactions."
        )

    if len(all_transactions) != 19:
        raise AssertionError(
            "Expected 19 transactions in total."
        )

    # --------------------------------------------------------
    # Snapshot all original test inputs.
    # --------------------------------------------------------

    original_snapshot = copy.deepcopy(all_transactions)

    gateway_snapshot = copy.deepcopy(GATEWAY_TRANSACTIONS)

    bank_settlement_snapshot = copy.deepcopy(
        BANK_SETTLEMENT_TRANSACTIONS
    )

    # --------------------------------------------------------
    # Unified reconciliation
    # --------------------------------------------------------

    heading("RUNNING UNIFIED RECONCILIATION")

    print("Incoming transactions:", len(all_transactions))
    print("Gateway transactions:", len(GATEWAY_TRANSACTIONS))
    print("Bank settlement transactions:", len(BANK_SETTLEMENT_TRANSACTIONS))

    print(
        "Consolidated opening balance:",
        CONSOLIDATED_OPENING_BALANCE,
    )

    print(
        "Consolidated closing balance:",
        CONSOLIDATED_CLOSING_BALANCE,
    )

    unified_result = reconcile_all_transactions(
        transactions=all_transactions,
        existing_transactions=None,
        accounts=TEST_ACCOUNTS,

        # Settlement engine receives synthetic in-memory data.
        gateway_transactions=GATEWAY_TRANSACTIONS,
        bank_transactions=BANK_SETTLEMENT_TRANSACTIONS,

        # Consolidated balance across both accounts.
        opening_balance=CONSOLIDATED_OPENING_BALANCE,
        closing_balance=CONSOLIDATED_CLOSING_BALANCE,

        balance_tolerance=Decimal("0.01"),

        # Do not check running balances across two separate accounts
        # as though they were one account.
        check_running_balance=False,

        max_transfer_date_gap_days=1,
        max_refund_date_gap_days=90,
        max_settlement_date_gap_days=5,
    )

    if not unified_result.get("success"):
        raise RuntimeError(
            "Unified reconciliation failed: "
            + str(unified_result.get("message"))
        )

    if unified_result.get("writes_performed") is not False:
        raise AssertionError(
            "Unexpected write operation reported by coordinator."
        )

    print("Unified reconciliation: SUCCESS")
    print("Mode:", unified_result.get("mode"))
    print("Writes performed:", unified_result.get("writes_performed"))

    print_engine_results(unified_result)

    # --------------------------------------------------------
    # Validate all five engines
    # --------------------------------------------------------

    regression_result = validate_all_engines(
        unified_result
    )

    # --------------------------------------------------------
    # Individual account balance reconciliation
    # --------------------------------------------------------

    primary_balance = run_balance_check(
        "PRIMARY ACCOUNT",
        primary_transactions,
        PRIMARY_OPENING_BALANCE,
        PRIMARY_CLOSING_BALANCE,
    )

    secondary_balance = run_balance_check(
        "SECONDARY ACCOUNT",
        secondary_transactions,
        SECONDARY_OPENING_BALANCE,
        SECONDARY_CLOSING_BALANCE,
    )

    # --------------------------------------------------------
    # Verify every input collection remains unchanged.
    # --------------------------------------------------------

    heading("INPUT IMMUTABILITY CHECK")

    transactions_unchanged = (
        all_transactions == original_snapshot
    )

    gateway_unchanged = (
        GATEWAY_TRANSACTIONS == gateway_snapshot
    )

    bank_settlement_unchanged = (
        BANK_SETTLEMENT_TRANSACTIONS == bank_settlement_snapshot
    )

    print(
        "Original bank transactions unchanged:",
        transactions_unchanged,
    )

    print(
        "Gateway transactions unchanged:",
        gateway_unchanged,
    )

    print(
        "Bank settlement transactions unchanged:",
        bank_settlement_unchanged,
    )

    if not transactions_unchanged:
        raise AssertionError(
            "A reconciliation engine modified original bank transactions."
        )

    if not gateway_unchanged:
        raise AssertionError(
            "Settlement engine modified gateway input transactions."
        )

    if not bank_settlement_unchanged:
        raise AssertionError(
            "Settlement engine modified bank settlement inputs."
        )

    # --------------------------------------------------------
    # Verify individual account balances
    # --------------------------------------------------------

    if primary_balance.get("statement_balanced") is not True:
        raise AssertionError(
            "Primary account balance did not reconcile."
        )

    if secondary_balance.get("statement_balanced") is not True:
        raise AssertionError(
            "Secondary account balance did not reconcile."
        )

    # --------------------------------------------------------
    # Final report
    # --------------------------------------------------------

    heading("FINAL INTEGRATION TEST REPORT")

    report = {
        "test_name": "November 2026 Full Reconciliation",
        "execution_mode": "real_engine_in_memory",

        "total_transactions": len(all_transactions),
        "primary_transactions": len(primary_transactions),
        "secondary_transactions": len(secondary_transactions),

        "unified_reconciliation_success": unified_result.get(
            "success"
        ),

        "engines_executed": list(
            unified_result.get("engines", {}).keys()
        ),

        "five_engine_regression": regression_result,

        "primary_balance_reconciled": primary_balance.get(
            "statement_balanced"
        ),

        "primary_balance_difference": primary_balance.get(
            "difference"
        ),

        "secondary_balance_reconciled": secondary_balance.get(
            "statement_balanced"
        ),

        "secondary_balance_difference": secondary_balance.get(
            "difference"
        ),

        "consolidated_balance_reconciled": (
            unified_result["engines"]["balance"].get(
                "statement_balanced"
            )
        ),

        "input_transactions_unchanged": transactions_unchanged,

        "gateway_transactions_unchanged": gateway_unchanged,

        "bank_settlement_transactions_unchanged": (
            bank_settlement_unchanged
        ),

        "database_writes": False,
        "chromadb_writes": False,

        "settlement_matching": "PASSED",
    }

    print_json(report)

    # --------------------------------------------------------
    # Final result
    # --------------------------------------------------------

    heading("INTEGRATION TEST FINISHED")

    print("PDF extraction: PASSED")
    print("Transaction parsing: PASSED")
    print("Transaction normalization: PASSED")
    print("Transaction validation: PASSED")

    print("Duplicate detection: PASSED")
    print("Internal transfer matching: PASSED")
    print("Refund matching: PASSED")
    print("Settlement matching: PASSED")
    print("Consolidated balance reconciliation: PASSED")

    print("Primary account running balance: PASSED")
    print("Secondary account running balance: PASSED")

    print("Input immutability: PASSED")

    print("MySQL writes: NONE")
    print("ChromaDB writes: NONE")

    heading("ALL FIVE RECONCILIATION ENGINES PASSED")

    print(
        "FinWell AI November reconciliation regression "
        "test completed successfully."
    )


if __name__ == "__main__":
    main()
