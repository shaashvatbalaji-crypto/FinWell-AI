
import sys
import re
from pathlib import Path
from decimal import Decimal


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
# 2. PRIMARY SYNTHETIC STATEMENT
# ---------------------------------------------------------

PRIMARY_PDF = Path(
    r"C:\Users\shaas\Downloads\finwell_reconciliation_primary_nov2026.pdf"
)

ACCOUNT = {
    "account_number": "4821",
    "account_id": "TEST_ACCOUNT_4821",
}


# ---------------------------------------------------------
# 3. HANDLE EXISTING CLEANER RETURN FORMAT
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
# 4. REUSE EXISTING PDF EXTRACTION AND PARSER
# ---------------------------------------------------------

def load_transactions():

    print("\nLoading primary PDF...")

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
        raise TypeError("PDF extraction did not return text.")

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
# 5. IDENTIFY AMAZON PURCHASE AND REFUNDS
# ---------------------------------------------------------

def find_amazon_purchase_and_refunds(transactions):

    purchase = None
    refunds = []

    for tx in transactions:

        description = tx["description"].upper()

        if "AMAZON" not in description:
            continue

        # Original purchase.
        if "PURCHASE" in description and tx["debit"] > 0:
            purchase = tx

        # Refund credits.
        elif "REFUND" in description and tx["credit"] > 0:
            refunds.append(tx)

    return purchase, refunds


# ---------------------------------------------------------
# 6. PARTIAL REFUND ALLOCATION DRY-RUN
# ---------------------------------------------------------

def reconcile_partial_refunds(purchase, refunds):

    purchase_amount = purchase["debit"]

    total_refunded = Decimal("0.00")
    allocations = []

    for refund in sorted(
        refunds,
        key=lambda tx: tx["date"]
    ):

        refund_amount = refund["credit"]

        remaining_before = purchase_amount - total_refunded

        if refund_amount <= 0:
            continue

        if refund_amount > remaining_before:
            raise ValueError(
                "Refund allocation exceeds the remaining purchase amount."
            )

        total_refunded += refund_amount

        allocations.append({
            "purchase_date": purchase["date"],
            "refund_date": refund["date"],
            "purchase_amount": purchase_amount,
            "refund_amount": refund_amount,
            "reference": "A501",
            "remaining_after": purchase_amount - total_refunded,
            "status": "candidate",
        })

    remaining_expense = purchase_amount - total_refunded

    return {
        "purchase_amount": purchase_amount,
        "total_refunded": total_refunded,
        "remaining_expense": remaining_expense,
        "allocations": allocations,
    }


# ---------------------------------------------------------
# 7. MAIN TEST
# ---------------------------------------------------------

def main():

    print("\n" + "=" * 65)
    print("FINWELL AI - PARTIAL REFUND RECONCILIATION DRY-RUN")
    print("=" * 65)

    transactions = load_transactions()

    assert len(transactions) == 14, (
        f"Expected 14 transactions, received {len(transactions)}"
    )

    purchase, refunds = find_amazon_purchase_and_refunds(
        transactions
    )

    assert purchase is not None, "Amazon purchase not found."

    assert len(refunds) == 2, (
        f"Expected 2 Amazon refunds, found {len(refunds)}"
    )

    result = reconcile_partial_refunds(
        purchase,
        refunds,
    )

    # -----------------------------------------------------
    # DISPLAY RESULTS
    # -----------------------------------------------------

    print("\n--- Original Purchase ---")

    print("Date:", purchase["date"])
    print("Description:", purchase["description"])
    print("Debit:", purchase["debit"])

    print("\n--- Refund Allocations ---")

    for index, allocation in enumerate(
        result["allocations"],
        start=1
    ):

        print(f"\nRefund {index}")

        for key, value in allocation.items():
            print(f"{key}: {value}")

    print("\n--- Refund Summary ---")

    print("Original purchase:", result["purchase_amount"])
    print("Total refunded:", result["total_refunded"])
    print("Remaining expense:", result["remaining_expense"])

    # -----------------------------------------------------
    # ASSERTIONS
    # -----------------------------------------------------

    assert result["purchase_amount"] == Decimal("3000.00")

    assert len(result["allocations"]) == 2

    assert result["total_refunded"] == Decimal("1500.00")

    assert result["remaining_expense"] == Decimal("1500.00")

    assert (
        result["allocations"][0]["refund_amount"]
        == Decimal("1000.00")
    )

    assert (
        result["allocations"][1]["refund_amount"]
        == Decimal("500.00")
    )

    assert (
        result["total_refunded"] + result["remaining_expense"]
        == result["purchase_amount"]
    )

    print("\n" + "=" * 65)
    print("ALL PARTIAL REFUND ASSERTIONS PASSED")
    print("=" * 65)

    print("PASS: Original purchase identified.")
    print("PASS: Two separate refunds identified.")
    print("PASS: Both refunds allocated to the same purchase.")
    print("PASS: Total refund is ₹1,500.")
    print("PASS: Remaining expense is ₹1,500.")
    print("PASS: No over-allocation.")
    print("PASS: No database or ChromaDB writes.")

    print("\nFinal status: SUCCESS")


if __name__ == "__main__":
    main()
