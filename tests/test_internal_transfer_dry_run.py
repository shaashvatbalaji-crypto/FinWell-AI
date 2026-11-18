
import sys
import re
from pathlib import Path
from decimal import Decimal


# ---------------------------------------------------------
# 1. PROJECT IMPORT PATH
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ---------------------------------------------------------
# 2. EXISTING FINWELL PIPELINE IMPORTS
# ---------------------------------------------------------

from pdf_extraction.pdf_validator import validate_pdf
from pdf_extraction.pdf_reader import extract_pdf_text
from preprocessing.text_cleaner import clean_extracted_text
from preprocessing.transaction_parser import parse_transactions


# ---------------------------------------------------------
# 3. TEST PDF PATHS
# ---------------------------------------------------------

PRIMARY_PDF = Path(
    r"C:\Users\shaas\Downloads\finwell_reconciliation_primary_nov2026.pdf"
)

SECONDARY_PDF = Path(
    r"C:\Users\shaas\Downloads\finwell_reconciliation_secondary_nov2026.pdf"
)


# Verified synthetic statement account metadata.
# This is attached only in memory for this test.

ACCOUNTS = {
    "primary": {
        "account_number": "4821",
        "account_id": "TEST_ACCOUNT_4821",
    },
    "secondary": {
        "account_number": "7392",
        "account_id": "TEST_ACCOUNT_7392",
    },
}


# ---------------------------------------------------------
# 4. NORMALIZE CLEANER OUTPUT
# ---------------------------------------------------------

def get_cleaned_text(cleaner_result):
    """
    Convert the existing cleaner's output into a string.

    Supports common return contracts:
    - str
    - dict containing cleaned text
    - tuple/list containing text
    """

    if isinstance(cleaner_result, str):
        return cleaner_result

    if isinstance(cleaner_result, dict):

        possible_keys = [
            "cleaned_text",
            "clean_text",
            "text",
            "content",
            "full_text",
            "extracted_text",
        ]

        for key in possible_keys:
            value = cleaner_result.get(key)

            if isinstance(value, str):
                return value

        raise TypeError(
            "Cleaner returned a dictionary, but no supported text field "
            f"was found. Available keys: {list(cleaner_result.keys())}"
        )

    if isinstance(cleaner_result, (tuple, list)):

        for value in cleaner_result:
            if isinstance(value, str):
                return value

        raise TypeError(
            "Cleaner returned a tuple/list without a string value."
        )

    raise TypeError(
        "Unsupported cleaner return type: "
        f"{type(cleaner_result).__name__}"
    )


# ---------------------------------------------------------
# 5. LOAD PDF USING EXISTING FINWELL FUNCTIONS
# ---------------------------------------------------------

def load_transactions(pdf_path: Path, account_metadata: dict) -> list:

    print("\n" + "-" * 60)
    print(f"Processing: {pdf_path.name}")
    print("-" * 60)

    # Check PDF existence.
    if not pdf_path.exists():
        raise FileNotFoundError(
            f"PDF not found: {pdf_path}"
        )

    # Step 1: Existing PDF validation.
    validation = validate_pdf(str(pdf_path))

    if not validation.get("valid"):
        raise ValueError(
            f"PDF validation failed: {validation.get('error')}"
        )

    print("PDF validation: PASS")

    # Step 2: Existing PDF extraction.
    extraction = extract_pdf_text(str(pdf_path))

    if not extraction.get("success"):
        raise ValueError(
            f"PDF extraction failed: {extraction.get('error')}"
        )

    raw_text = extraction.get("full_text")

    if not isinstance(raw_text, str):
        raise TypeError(
            "PDF extraction did not return full_text as a string. "
            f"Received: {type(raw_text).__name__}"
        )

    print("PDF extraction: PASS")
    print(f"Extracted characters: {len(raw_text)}")

    # Step 3: Existing FinWell preprocessing cleaner.
    cleaner_result = clean_extracted_text(raw_text)

    # Adapt cleaner output to the parser's string input contract.
    cleaned_text = get_cleaned_text(cleaner_result)

    if not cleaned_text.strip():
        raise ValueError(
            "Cleaned PDF text is empty."
        )

    print("Text cleaning: PASS")
    print(f"Cleaner return type: {type(cleaner_result).__name__}")
    print(f"Cleaned characters: {len(cleaned_text)}")

    # Step 4: Existing transaction parser.
    parsed = parse_transactions(cleaned_text)

    if not isinstance(parsed, dict):
        raise TypeError(
            "Parser returned an unexpected result type: "
            f"{type(parsed).__name__}"
        )

    if not parsed.get("success"):
        raise ValueError(
            f"Transaction parsing failed: {parsed.get('error')}"
        )

    extracted_transactions = parsed.get("transactions", [])

    transactions = []

    # Step 5: Attach verified account metadata in memory.
    for item in extracted_transactions:

        transaction = dict(item)

        transaction["account_id"] = account_metadata["account_id"]
        transaction["account_number"] = account_metadata["account_number"]

        transaction["debit"] = Decimal(
            str(transaction.get("debit") or 0)
        ).quantize(Decimal("0.01"))

        transaction["credit"] = Decimal(
            str(transaction.get("credit") or 0)
        ).quantize(Decimal("0.01"))

        transactions.append(transaction)

    print("Transaction parsing: PASS")
    print(f"Transactions extracted: {len(transactions)}")

    return transactions


# ---------------------------------------------------------
# 6. EXTRACT TRANSACTION REFERENCE
# ---------------------------------------------------------

def extract_reference(description: str):

    match = re.search(
        r"\bREF\s+([A-Z0-9]+)\b",
        description.upper()
    )

    return match.group(1) if match else None


# ---------------------------------------------------------
# 7. INTERNAL TRANSFER MATCHING - DRY RUN
# ---------------------------------------------------------

def find_internal_transfer_candidates(
    primary_transactions: list,
    secondary_transactions: list,
) -> list:

    candidates = []

    for debit_tx in primary_transactions:

        # Source account must have a debit.
        if debit_tx["debit"] <= 0:
            continue

        for credit_tx in secondary_transactions:

            # Destination account must have a credit.
            if credit_tx["credit"] <= 0:
                continue

            # Amount must match exactly.
            if debit_tx["debit"] != credit_tx["credit"]:
                continue

            # Transaction references must match.
            debit_reference = extract_reference(
                debit_tx["description"]
            )

            credit_reference = extract_reference(
                credit_tx["description"]
            )

            if not debit_reference:
                continue

            if debit_reference != credit_reference:
                continue

            # Transaction dates must match.
            if debit_tx["date"] != credit_tx["date"]:
                continue

            debit_description = debit_tx["description"].upper()
            credit_description = credit_tx["description"].upper()

            # Verify transfer direction and account references.
            if "TO OWN AC 7392" not in debit_description:
                continue

            if "FROM OWN AC 4821" not in credit_description:
                continue

            candidates.append({
                "date": debit_tx["date"],
                "amount": debit_tx["debit"],
                "reference": debit_reference,
                "source_account": debit_tx["account_number"],
                "target_account": credit_tx["account_number"],
                "source_description": debit_tx["description"],
                "target_description": credit_tx["description"],
                "status": "candidate",
            })

    return candidates


# ---------------------------------------------------------
# 8. DISPLAY RESULTS
# ---------------------------------------------------------

def display_candidates(candidates):

    print("\n" + "=" * 65)
    print("INTERNAL TRANSFER RECONCILIATION RESULTS")
    print("=" * 65)

    if not candidates:
        print("No internal transfer candidates found.")
        return

    for index, candidate in enumerate(candidates, start=1):

        print(f"\nCandidate {index}")

        for key, value in candidate.items():
            print(f"{key}: {value}")


# ---------------------------------------------------------
# 9. MAIN DRY-RUN TEST
# ---------------------------------------------------------

def main():

    print("\n")
    print("=" * 65)
    print("FINWELL AI - INTERNAL TRANSFER DRY-RUN")
    print("=" * 65)

    # Load primary account statement.
    primary_transactions = load_transactions(
        PRIMARY_PDF,
        ACCOUNTS["primary"],
    )

    # Load secondary account statement.
    secondary_transactions = load_transactions(
        SECONDARY_PDF,
        ACCOUNTS["secondary"],
    )

    print("\n" + "=" * 65)
    print("EXTRACTION SUMMARY")
    print("=" * 65)

    print(
        f"Account 4821 transactions: "
        f"{len(primary_transactions)}"
    )

    print(
        f"Account 7392 transactions: "
        f"{len(secondary_transactions)}"
    )

    # Run in-memory transfer matching.
    candidates = find_internal_transfer_candidates(
        primary_transactions,
        secondary_transactions,
    )

    display_candidates(candidates)

    # -----------------------------------------------------
    # EXPECTED TEST ASSERTIONS
    # -----------------------------------------------------

    assert len(primary_transactions) == 14, (
        f"Expected 14 primary transactions, "
        f"received {len(primary_transactions)}"
    )

    assert len(secondary_transactions) == 5, (
        f"Expected 5 secondary transactions, "
        f"received {len(secondary_transactions)}"
    )

    assert len(candidates) == 1, (
        f"Expected 1 transfer candidate, "
        f"received {len(candidates)}"
    )

    candidate = candidates[0]

    assert candidate["amount"] == Decimal("5000.00")
    assert candidate["reference"] == "TRF501"
    assert candidate["date"] == "2026-11-06"
    assert candidate["source_account"] == "4821"
    assert candidate["target_account"] == "7392"
    assert candidate["status"] == "candidate"

    # -----------------------------------------------------
    # FINAL RESULT
    # -----------------------------------------------------

    print("\n" + "=" * 65)
    print("ALL INTERNAL TRANSFER DRY-RUN ASSERTIONS PASSED")
    print("=" * 65)

    print("PASS: Both PDFs validated and extracted.")
    print("PASS: Existing FinWell text cleaner executed.")
    print("PASS: Existing transaction parser executed.")
    print("PASS: 14 primary transactions extracted.")
    print("PASS: 5 secondary transactions extracted.")
    print("PASS: ₹5,000 transfer candidate identified.")
    print("PASS: Reference TRF501 verified.")
    print("PASS: Transaction date verified.")
    print("PASS: Transfer direction verified.")

    print("\nNo MySQL writes were performed.")
    print("No ChromaDB writes were performed.")
    print("No production ingestion was triggered.")

    print("\nFinal status: SUCCESS")


if __name__ == "__main__":
    main()
