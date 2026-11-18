
import sys
import re
from pathlib import Path
from decimal import Decimal
from datetime import date


# ---------------------------------------------------------
# 1. PROJECT PATH AND EXISTING FINWELL IMPORTS
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pdf_extraction.pdf_validator import validate_pdf
from pdf_extraction.pdf_reader import extract_pdf_text
from preprocessing.text_cleaner import clean_extracted_text
from preprocessing.transaction_parser import parse_transactions


# ---------------------------------------------------------
# 2. PRIMARY SYNTHETIC PDF
# ---------------------------------------------------------

PRIMARY_PDF = Path(
    r"C:\Users\shaas\Downloads\finwell_reconciliation_primary_nov2026.pdf"
)

ACCOUNT = {
    "account_id": "TEST_ACCOUNT_4821",
    "account_number": "4821",
}


# ---------------------------------------------------------
# 3. CLEANER OUTPUT ADAPTER
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
# 4. EXISTING PDF EXTRACTION PIPELINE
# ---------------------------------------------------------

def load_transactions():

    print("\nLoading primary statement...")

    if not PRIMARY_PDF.exists():
        raise FileNotFoundError(PRIMARY_PDF)

    validation = validate_pdf(str(PRIMARY_PDF))

    if not validation.get("valid"):
        raise ValueError(validation.get("error"))

    extraction = extract_pdf_text(str(PRIMARY_PDF))

    if not extraction.get("success"):
        raise ValueError(extraction.get("error"))

    raw_text = extraction.get("full_text")

    if not isinstance(raw_text, str):
        raise TypeError("PDF extraction did not return a string.")

    cleaner_result = clean_extracted_text(raw_text)
    cleaned_text = get_cleaned_text(cleaner_result)

    parsed = parse_transactions(cleaned_text)

    if not parsed.get("success"):
        raise ValueError(parsed.get("error"))

    transactions = []

    for item in parsed.get("transactions", []):

        tx = dict(item)

        tx["account_id"] = ACCOUNT["account_id"]
        tx["account_number"] = ACCOUNT["account_number"]

        tx["debit"] = Decimal(
            str(tx.get("debit") or 0)
        ).quantize(Decimal("0.01"))

        tx["credit"] = Decimal(
            str(tx.get("credit") or 0)
        ).quantize(Decimal("0.01"))

        transactions.append(tx)

    print(f"Extracted transactions: {len(transactions)}")

    return transactions


# ---------------------------------------------------------
# 5. REFERENCE EXTRACTION
# ---------------------------------------------------------

def extract_reference(description):

    match = re.search(
        r"\bREF\s+([A-Z0-9]+)\b",
        description.upper()
    )

    return match.group(1) if match else None


# ---------------------------------------------------------
# 6. TRANSACTION COMPARISON
# ---------------------------------------------------------

def transaction_amount(tx):

    if tx["debit"] > 0 and tx["credit"] > 0:
        raise ValueError("Transaction has both debit and credit.")

    if tx["debit"] > 0:
        return tx["debit"], "debit"

    if tx["credit"] > 0:
        return tx["credit"], "credit"

    return Decimal("0.00"), "zero"


def compare_transactions(tx1, tx2):

    """
    Conservative dry-run duplicate candidate logic.

    Strong matching requires:
    - Same user/account context in this single-account test.
    - Same transaction direction.
    - Same amount.
    - Same date.
    - Same explicit reference.

    A matching merchant and amount alone are insufficient.
    """

    if tx1 is tx2:
        return None

    if tx1["account_id"] != tx2["account_id"]:
        return None

    amount1, direction1 = transaction_amount(tx1)
    amount2, direction2 = transaction_amount(tx2)

    if amount1 == 0 or amount2 == 0:
        return None

    if direction1 != direction2:
        return None

    if amount1 != amount2:
        return None

    if tx1["date"] != tx2["date"]:
        return None

    reference1 = extract_reference(tx1["description"])
    reference2 = extract_reference(tx2["description"])

    if not reference1 or not reference2:
        return None

    if reference1 != reference2:
        return None

    return {
        "date": tx1["date"],
        "amount": amount1,
        "direction": direction1,
        "reference": reference1,
        "description_1": tx1["description"],
        "description_2": tx2["description"],
        "status": "candidate",
    }


# ---------------------------------------------------------
# 7. RUN DUPLICATE DETECTION
# ---------------------------------------------------------

def find_duplicate_candidates(transactions):

    candidates = []

    for i in range(len(transactions)):

        for j in range(i + 1, len(transactions)):

            result = compare_transactions(
                transactions[i],
                transactions[j],
            )

            if result:
                result["transaction_index_1"] = i
                result["transaction_index_2"] = j
                candidates.append(result)

    return candidates


# ---------------------------------------------------------
# 8. TEST LEGITIMATE SEPARATE PAYMENTS
# ---------------------------------------------------------

def find_upi_payments(transactions):

    results = []

    for tx in transactions:

        description = tx["description"].upper()

        if (
            "UPI PAYMENT" in description
            and tx["debit"] == Decimal("2000.00")
        ):
            results.append(tx)

    return results


# ---------------------------------------------------------
# 9. MAIN TEST
# ---------------------------------------------------------

def main():

    print("\n" + "=" * 65)
    print("FINWELL AI - DUPLICATE DETECTION DRY-RUN")
    print("=" * 65)

    transactions = load_transactions()

    assert len(transactions) == 14

    candidates = find_duplicate_candidates(transactions)

    print("\n--- Duplicate Candidates ---")

    if not candidates:
        print("No duplicate candidates found.")
    else:
        for index, candidate in enumerate(candidates, start=1):

            print(f"\nCandidate {index}")

            for key, value in candidate.items():
                print(f"{key}: {value}")

    # -----------------------------------------------------
    # UPI LEGITIMATE PAYMENT CHECK
    # -----------------------------------------------------

    print("\n--- Legitimate UPI Payment Check ---")

    upi_payments = find_upi_payments(transactions)

    assert len(upi_payments) == 2, (
        f"Expected 2 independent UPI payments, got {len(upi_payments)}"
    )

    upi_payments.sort(key=lambda tx: tx["date"])

    for tx in upi_payments:

        print(
            f"Date: {tx['date']} | "
            f"Amount: {tx['debit']} | "
            f"Reference: {extract_reference(tx['description'])}"
        )

    assert upi_payments[0]["date"] == "2026-11-15"
    assert upi_payments[1]["date"] == "2026-11-25"

    assert (
        extract_reference(upi_payments[0]["description"])
        == "UPI801"
    )

    assert (
        extract_reference(upi_payments[1]["description"])
        == "UPI901"
    )

    # -----------------------------------------------------
    # FINAL ASSERTIONS
    # -----------------------------------------------------

    # This statement has no deliberately repeated transaction
    # with the same date, amount, direction and reference.
    assert len(candidates) == 0, (
        "Unexpected duplicate candidate found."
    )

    print("\n" + "=" * 65)
    print("DUPLICATE DETECTION TEST PASSED")
    print("=" * 65)

    print("PASS: 14 transactions loaded.")
    print("PASS: No false duplicate identified.")
    print("PASS: Two ₹2,000 UPI payments remain separate.")
    print("PASS: Different UPI references preserved.")
    print("PASS: No database or ChromaDB writes.")

    print("\nFinal status: SUCCESS")


if __name__ == "__main__":
    main()
