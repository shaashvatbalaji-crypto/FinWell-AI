from preprocessing.data_normalizer import (
    normalize_date,
    normalize_amount,
    normalize_description,
    normalize_transaction,
    normalize_transactions,
)


def test_normalize_date():
    assert normalize_date("03/11/2026") == "2026-11-03"
    assert normalize_date("03-11-2026") == "2026-11-03"
    assert normalize_date("2026-11-03") == "2026-11-03"

    print("PASS: Dates normalized")


def test_normalize_amount():
    assert normalize_amount("₹1,250.50") == 1250.50
    assert normalize_amount("(250.00)") == -250.00
    assert normalize_amount("100") == 100.00
    assert normalize_amount(None) is None
    assert normalize_amount("invalid") is None

    print("PASS: Amounts normalized")


def test_normalize_description():
    result = normalize_description("  Grocery   Store \t Chennai  ")

    assert result == "Grocery Store Chennai"

    print("PASS: Descriptions normalized")


def test_normalize_transaction():
    transaction = {
        "date": "03/11/2026",
        "description": "  Electricity   Bill ",
        "debit": "1,800.00",
        "credit": "0.00",
        "balance": "27,950.00",
    }

    result = normalize_transaction(transaction)

    assert result["success"] is True
    assert result["transaction"]["date"] == "2026-11-03"
    assert result["transaction"]["description"] == "Electricity Bill"
    assert result["transaction"]["debit"] == 1800.00
    assert result["transaction"]["credit"] == 0.00
    assert result["transaction"]["balance"] == 27950.00

    print("PASS: Transaction normalized")


def test_normalize_transactions():
    transactions = [
        {
            "date": "01-11-2026",
            "description": "Grocery Store",
            "debit": "250.00",
            "credit": "0.00",
            "balance": "4750.00",
        },
        {
            "date": "02-11-2026",
            "description": "Monthly Salary",
            "debit": "0.00",
            "credit": "25000.00",
            "balance": "29750.00",
        },
    ]

    result = normalize_transactions(transactions)

    assert result["success"] is True
    assert result["total_transactions"] == 2
    assert result["transactions"][1]["credit"] == 25000.00

    print("PASS: Transaction list normalized")


def test_invalid_inputs():
    result = normalize_transaction("not a dictionary")

    assert result["success"] is False

    result = normalize_transactions("not a list")

    assert result["success"] is False

    print("PASS: Invalid inputs handled")


if __name__ == "__main__":
    test_normalize_date()
    test_normalize_amount()
    test_normalize_description()
    test_normalize_transaction()
    test_normalize_transactions()
    test_invalid_inputs()

    print("\nAll data normalizer tests passed!")