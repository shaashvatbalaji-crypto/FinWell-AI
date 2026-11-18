
import sys
import re
from pathlib import Path
from decimal import Decimal
from itertools import combinations
from collections import Counter

# ---------------------------------------------------------
# 1. PROJECT PATH
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ---------------------------------------------------------
# 2. EXISTING FINWELL IMPORTS
# ---------------------------------------------------------

from pdf_extraction.pdf_validator import validate_pdf
from pdf_extraction.pdf_reader import extract_pdf_text
from preprocessing.text_cleaner import clean_extracted_text
from preprocessing.transaction_parser import parse_transactions
from preprocessing.data_normalizer import normalize_transactions
from preprocessing.data_validator import validate_transactions

from reconciliation.duplicate_detector import detect_duplicate_candidate


# ---------------------------------------------------------
# 3. PDF PATHS AND TEST METADATA
# ---------------------------------------------------------

PRIMARY_PDF = Path(
    r"C:\Users\shaas\Downloads\finwell_reconciliation_primary_nov2026.pdf"
)

SECONDARY_PDF = Path(
    r"C:\Users\shaas\Downloads\finwell_reconciliation_secondary_nov2026.pdf"
)

TEST_USER_ID = 999999

ACCOUNTS = {
    "PRIMARY": {
        "account_id": "TEST_ACCOUNT_4821",
        "document_id": 9001,
        "account_number": "4821",
        "path": PRIMARY_PDF,
    },
    "SECONDARY": {
        "account_id": "TEST_ACCOUNT_7392",
        "document_id": 9002,
        "account_number": "7392",
        "path": SECONDARY_PDF,
    },
}


# ---------------------------------------------------------
# 4. CLEANER OUTPUT ADAPTER
# ---------------------------------------------------------

def get_cleaned_text(result):

    if isinstance(result, str):
        return result

    if isinstance(result, dict):

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

        raise TypeError(
            f"Unsupported cleaner dictionary keys: {list(result.keys())}"
        )

    if isinstance(result, (tuple, list)):

        for value in result:
            if isinstance(value, str):
                return value

    raise TypeError(
        f"Unsupported cleaner result: {type(result).__name__}"
    )


# ---------------------------------------------------------
# 5. LOAD AND PROCESS ONE PDF
# ---------------------------------------------------------

def load_pdf_transactions(account_name, metadata):

    pdf_path = metadata["path"]

    print("\n" + "=" * 65)
    print(f"PROCESSING {account_name}")
    print("=" * 65)

    if not pdf_path.exists():
        raise FileNotFoundError(pdf_path)

    # PDF validation
    validation = validate_pdf(str(pdf_path))

    if not validation.get("valid"):
        raise ValueError(
            f"PDF validation failed: {validation.get('error')}"
        )

    # PDF extraction
    extraction = extract_pdf_text(str(pdf_path))

    if not extraction.get("success"):
        raise ValueError(
            f"PDF extraction failed: {extraction.get('error')}"
        )

    raw_text = extraction.get("full_text")

    if not isinstance(raw_text, str):
        raise TypeError("PDF extraction did not return text.")

    # Actual ingestion cleaner
    cleaner_result = clean_extracted_text(raw_text)
    cleaned_text = get_cleaned_text(cleaner_result)

    # Actual parser
    parsing = parse_transactions(cleaned_text)

    if not parsing.get("success"):
        raise ValueError(
            f"Parsing failed: {parsing.get('error')}"
        )

    parsed = parsing.get("transactions", [])

    # Actual normalizer
    normalization = normalize_transactions(parsed)

    if not normalization.get("success"):
        raise ValueError(
            f"Normalization failed: {normalization.get('error')}"
        )

    normalized = normalization.get("transactions", [])

    # Actual transaction validator
    validation_result = validate_transactions(normalized)

    if not validation_result.get("success"):
        raise ValueError("Transaction validation failed.")

    valid_transactions = validation_result.get(
        "valid_transactions", []
    )

    invalid_count = validation_result.get("invalid_count", 0)

    print(f"PDF: {pdf_path.name}")
    print(f"Parsed: {len(parsed)}")
    print(f"Normalized: {len(normalized)}")
    print(f"Valid: {len(valid_transactions)}")
    print(f"Invalid: {invalid_count}")

    if invalid_count != 0:
        raise AssertionError(
            f"{account_name}: Expected zero invalid transactions."
        )

    if len(valid_transactions) != len(parsed):
        raise AssertionError(
            f"{account_name}: Transaction count changed during validation."
        )

    return valid_transactions


# ---------------------------------------------------------
# 6. BUILD EPHEMERAL PRODUCTION DETECTOR INPUTS
# ---------------------------------------------------------

def build_detector_transactions():

    all_transactions = []
    next_id = 1

    for account_name, metadata in ACCOUNTS.items():

        valid_transactions = load_pdf_transactions(
            account_name,
            metadata,
        )

        for item in valid_transactions:

            tx = dict(item)

            # Map normalized fields to the production detector contract.
            transaction_date = (
                tx.get("date")
                or tx.get("transaction_date")
            )

            if not transaction_date:
                raise ValueError(
                    f"Missing date in transaction: {tx}"
                )

            tx["transaction_id"] = next_id
            tx["user_id"] = TEST_USER_ID
            tx["document_id"] = metadata["document_id"]
            tx["account_id"] = metadata["account_id"]
            tx["transaction_date"] = transaction_date

            tx["debit"] = Decimal(
                str(tx.get("debit") or 0)
            ).quantize(Decimal("0.01"))

            tx["credit"] = Decimal(
                str(tx.get("credit") or 0)
            ).quantize(Decimal("0.01"))

            if not tx.get("description"):
                raise ValueError(
                    f"Missing description: {tx}"
                )

            all_transactions.append(tx)
            next_id += 1

    return all_transactions


# ---------------------------------------------------------
# 7. REFERENCE EXTRACTION FOR TEST REPORTING
# ---------------------------------------------------------

def extract_reference(description):

    match = re.search(
        r"\bREF\s+([A-Z0-9]+)\b",
        str(description).upper(),
    )

    return match.group(1) if match else None


def amount_and_direction(tx):

    debit = tx["debit"]
    credit = tx["credit"]

    if debit > 0 and credit > 0:
        raise ValueError("Both debit and credit are positive.")

    if debit > 0:
        return debit, "debit"

    if credit > 0:
        return credit, "credit"

    return Decimal("0.00"), "zero"


# ---------------------------------------------------------
# 8. RUN THE ACTUAL PRODUCTION DETECTOR
# ---------------------------------------------------------

def run_production_detector(transactions):

    candidates = []
    rejected = Counter()

    total_pairs = 0

    for tx1, tx2 in combinations(transactions, 2):

        total_pairs += 1

        result = detect_duplicate_candidate(tx1, tx2)

        if result.get("is_candidate"):

            candidate = dict(result)

            candidate["account_1"] = tx1["account_id"]
            candidate["account_2"] = tx2["account_id"]

            candidate["date_1"] = tx1["transaction_date"]
            candidate["date_2"] = tx2["transaction_date"]

            candidate["description_1"] = tx1["description"]
            candidate["description_2"] = tx2["description"]

            candidate["reference_1"] = extract_reference(
                tx1["description"]
            )

            candidate["reference_2"] = extract_reference(
                tx2["description"]
            )

            candidates.append(candidate)

        else:

            reason = result.get("reason", "Unknown")
            rejected[reason] += 1

    print("\n" + "=" * 65)
    print("PRODUCTION DETECTOR RESULTS")
    print("=" * 65)

    print(f"Total transactions: {len(transactions)}")
    print(f"Total pairs compared: {total_pairs}")
    print(f"Duplicate candidates: {len(candidates)}")
    print(f"Rejected comparisons: {sum(rejected.values())}")

    if candidates:

        print("\n--- DUPLICATE CANDIDATES ---")

        for index, candidate in enumerate(candidates, start=1):

            print(f"\nCANDIDATE {index}")

            for key, value in candidate.items():
                print(f"{key}: {value}")

    else:

        print("\nNo duplicate candidates identified.")

    print("\n--- REJECTION REASONS ---")

    for reason, count in rejected.most_common():
        print(f"{reason}: {count}")

    return candidates


# ---------------------------------------------------------
# 9. IDENTIFY IMPORTANT TEST TRANSACTIONS
# ---------------------------------------------------------

def find_by_reference(transactions, reference):

    return [
        tx for tx in transactions
        if extract_reference(tx["description"]) == reference
    ]


def find_upi_payments(transactions):

    return [
        tx for tx in transactions
        if (
            "UPI PAYMENT" in tx["description"].upper()
            and tx["debit"] == Decimal("2000.00")
        )
    ]


def run_scenario_checks(transactions, candidates):

    print("\n" + "=" * 65)
    print("FINANCIAL SCENARIO CHECKS")
    print("=" * 65)

    candidate_pairs = {
        frozenset((
            candidate["transaction_id"],
            candidate["matched_transaction_id"],
        ))
        for candidate in candidates
    }

    # 1. Internal transfer
    transfer_debit = find_by_reference(
        transactions, "TRF501"
    )

    assert len(transfer_debit) == 2

    debit_transactions = [
        tx for tx in transfer_debit
        if tx["debit"] == Decimal("5000.00")
    ]

    credit_transactions = [
        tx for tx in transfer_debit
        if tx["credit"] == Decimal("5000.00")
    ]

    assert len(debit_transactions) == 1
    assert len(credit_transactions) == 1

    debit_tx = debit_transactions[0]
    credit_tx = credit_transactions[0]

    assert debit_tx["account_id"] != credit_tx["account_id"]

    transfer_pair = frozenset((
        debit_tx["transaction_id"],
        credit_tx["transaction_id"],
    ))

    assert transfer_pair not in candidate_pairs

    print("PASS: ₹5,000 internal transfer is not a duplicate candidate.")

    # 2. Amazon purchase and partial refunds
    amazon_transactions = find_by_reference(
        transactions, "A501"
    )

    assert len(amazon_transactions) == 3

    purchases = [
        tx for tx in amazon_transactions
        if tx["debit"] == Decimal("3000.00")
    ]

    refunds = [
        tx for tx in amazon_transactions
        if tx["credit"] in (
            Decimal("1000.00"),
            Decimal("500.00"),
        )
    ]

    assert len(purchases) == 1
    assert len(refunds) == 2

    total_refunds = sum(
        (tx["credit"] for tx in refunds),
        Decimal("0.00"),
    )

    remaining_expense = (
        purchases[0]["debit"] - total_refunds
    )

    assert total_refunds == Decimal("1500.00")
    assert remaining_expense == Decimal("1500.00")

    refund_pair = frozenset((
        refunds[0]["transaction_id"],
        refunds[1]["transaction_id"],
    ))

    assert refund_pair not in candidate_pairs

    print("PASS: Amazon purchase and two partial refunds remain separate.")
    print(f"      Purchase: ₹{purchases[0]['debit']}")
    print(f"      Total refunds: ₹{total_refunds}")
    print(f"      Remaining expense: ₹{remaining_expense}")

    # 3. Independent UPI payments
    upi_payments = find_upi_payments(transactions)

    assert len(upi_payments) == 2

    upi_payments.sort(
        key=lambda tx: tx["transaction_date"]
    )

    assert upi_payments[0]["transaction_date"] == "2026-11-15"
    assert upi_payments[1]["transaction_date"] == "2026-11-25"

    assert extract_reference(
        upi_payments[0]["description"]
    ) == "UPI801"

    assert extract_reference(
        upi_payments[1]["description"]
    ) == "UPI901"

    upi_pair = frozenset((
        upi_payments[0]["transaction_id"],
        upi_payments[1]["transaction_id"],
    ))

    assert upi_pair not in candidate_pairs

    print("PASS: Two independent ₹2,000 UPI payments remain separate.")

    # 4. Check for cross-account candidates.
    cross_account_candidates = [
        candidate for candidate in candidates
        if candidate["account_1"] != candidate["account_2"]
    ]

    print(
        "\nCross-account duplicate candidates:",
        len(cross_account_candidates),
    )

    if cross_account_candidates:
        print(
            "WARNING: Production detector generated cross-account "
            "duplicate candidates. These require stricter review."
        )

    return cross_account_candidates


# ---------------------------------------------------------
# 10. MAIN
# ---------------------------------------------------------

def main():

    print("=" * 65)
    print("FINWELL AI - 19 TRANSACTION PRODUCTION COMPARISON")
    print("=" * 65)

    transactions = build_detector_transactions()

    assert len(transactions) == 19, (
        f"Expected 19 transactions, got {len(transactions)}"
    )

    primary_count = sum(
        tx["account_id"] == "TEST_ACCOUNT_4821"
        for tx in transactions
    )

    secondary_count = sum(
        tx["account_id"] == "TEST_ACCOUNT_7392"
        for tx in transactions
    )

    assert primary_count == 14
    assert secondary_count == 5

    print("\n--- INPUT SUMMARY ---")
    print(f"Primary transactions: {primary_count}")
    print(f"Secondary transactions: {secondary_count}")
    print(f"Total transactions: {len(transactions)}")

    candidates = run_production_detector(transactions)

    cross_account_candidates = run_scenario_checks(
        transactions,
        candidates,
    )

    print("\n" + "=" * 65)
    print("FINAL TEST SUMMARY")
    print("=" * 65)

    print("PASS: 19 validated transactions loaded.")
    print("PASS: Actual production duplicate detector executed.")
    print("PASS: Internal transfer scenario checked.")
    print("PASS: Partial refund scenario checked.")
    print("PASS: Independent UPI payments checked.")

    print(
        "Cross-account candidates requiring review:",
        len(cross_account_candidates),
    )

    print("\nNo MySQL writes.")
    print("No ChromaDB writes.")
    print("No production code modified.")
    print("All reconciliation IDs are temporary in-memory IDs.")

    print("\nFINAL STATUS: SCENARIO TESTS COMPLETED")


if __name__ == "__main__":
    main()
