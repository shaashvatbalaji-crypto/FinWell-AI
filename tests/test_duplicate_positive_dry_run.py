
from decimal import Decimal


def make_transaction(date, description, debit, credit=0):
    return {
        "date": date,
        "description": description,
        "debit": Decimal(str(debit)),
        "credit": Decimal(str(credit)),
        "account_id": "TEST_ACCOUNT_4821",
    }


def extract_reference(description):
    import re

    match = re.search(
        r"\bREF\s+([A-Z0-9]+)\b",
        description.upper()
    )

    return match.group(1) if match else None


def compare_transactions(tx1, tx2):
    """Conservative exact duplicate candidate test."""

    if tx1 is tx2:
        return None

    if tx1["account_id"] != tx2["account_id"]:
        return None

    if tx1["debit"] > 0 and tx1["credit"] > 0:
        return None

    if tx2["debit"] > 0 and tx2["credit"] > 0:
        return None

    amount1 = tx1["debit"] or tx1["credit"]
    amount2 = tx2["debit"] or tx2["credit"]

    direction1 = "debit" if tx1["debit"] > 0 else "credit"
    direction2 = "debit" if tx2["debit"] > 0 else "credit"

    if amount1 <= 0 or amount2 <= 0:
        return None

    if amount1 != amount2:
        return None

    if direction1 != direction2:
        return None

    if tx1["date"] != tx2["date"]:
        return None

    reference1 = extract_reference(tx1["description"])
    reference2 = extract_reference(tx2["description"])

    if not reference1 or reference1 != reference2:
        return None

    return {
        "amount": amount1,
        "date": tx1["date"],
        "reference": reference1,
        "status": "candidate",
    }


def main():

    print("=" * 65)
    print("FINWELL AI - POSITIVE DUPLICATE DETECTION TEST")
    print("=" * 65)

    # Case 1: Same transaction represented twice.
    transaction_a = make_transaction(
        "2026-11-05",
        "AMAZON PURCHASE REF A501",
        "3000.00",
    )

    transaction_b = make_transaction(
        "2026-11-05",
        "AMAZON PURCHASE REF A501",
        "3000.00",
    )

    result = compare_transactions(transaction_a, transaction_b)

    assert result is not None
    assert result["amount"] == Decimal("3000.00")
    assert result["date"] == "2026-11-05"
    assert result["reference"] == "A501"

    print("\nCASE 1: Exact repeated transaction")
    print("PASS: Duplicate candidate detected.")
    print(result)

    # Case 2: Different reference.
    transaction_c = make_transaction(
        "2026-11-05",
        "AMAZON PURCHASE REF A502",
        "3000.00",
    )

    result_different_reference = compare_transactions(
        transaction_a,
        transaction_c,
    )

    assert result_different_reference is None

    print("\nCASE 2: Different transaction reference")
    print("PASS: Not flagged as an exact duplicate.")

    # Case 3: Different date.
    transaction_d = make_transaction(
        "2026-11-06",
        "AMAZON PURCHASE REF A501",
        "3000.00",
    )

    result_different_date = compare_transactions(
        transaction_a,
        transaction_d,
    )

    assert result_different_date is None

    print("\nCASE 3: Different transaction date")
    print("PASS: Not flagged as an exact duplicate.")

    # Case 4: Different amount.
    transaction_e = make_transaction(
        "2026-11-05",
        "AMAZON PURCHASE REF A501",
        "2500.00",
    )

    result_different_amount = compare_transactions(
        transaction_a,
        transaction_e,
    )

    assert result_different_amount is None

    print("\nCASE 4: Different transaction amount")
    print("PASS: Not flagged as an exact duplicate.")

    print("\n" + "=" * 65)
    print("ALL POSITIVE DUPLICATE TESTS PASSED")
    print("=" * 65)
    print("No database writes.")
    print("No ChromaDB writes.")
    print("No production transactions modified.")


if __name__ == "__main__":
    main()
