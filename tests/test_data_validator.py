from preprocessing.data_validator import (
    validate_date,
    validate_amount,
    validate_transaction,
    validate_transactions,
)


def valid_transaction():
    return {
        "date": "2026-11-01",
        "description": "Grocery Store",
        "debit": 250.00,
        "credit": 0.00,
        "balance": 4750.00,
    }


def test_valid_date():
    assert validate_date("2026-11-01") is True
    assert validate_date("2026-02-30") is False
    assert validate_date("01-11-2026") is False

    print("PASS: Date validation")


def test_valid_amount():
    assert validate_amount(250.00) is True
    assert validate_amount(None) is True
    assert validate_amount("invalid") is False

    print("PASS: Amount validation")


def test_valid_transaction():
    result = validate_transaction(valid_transaction())

    assert result["valid"] is True
    assert result["errors"] == []

    print("PASS: Valid transaction accepted")


def test_missing_required_fields():
    transaction = valid_transaction()
    transaction["date"] = ""
    transaction["description"] = ""

    result = validate_transaction(transaction)

    assert result["valid"] is False
    assert any("date" in error.lower() for error in result["errors"])
    assert any("description" in error.lower() for error in result["errors"])

    print("PASS: Missing required fields detected")


def test_debit_and_credit_both_positive():
    transaction = valid_transaction()
    transaction["debit"] = 100.00
    transaction["credit"] = 200.00

    result = validate_transaction(transaction)

    assert result["valid"] is False
    assert any("both be positive" in error for error in result["errors"])

    print("PASS: Conflicting debit and credit detected")


def test_negative_debit_rejected():
    transaction = valid_transaction()
    transaction["debit"] = -100.00

    result = validate_transaction(transaction)

    assert result["valid"] is False
    assert any("debit cannot be negative" in error.lower()
               for error in result["errors"])

    print("PASS: Negative debit detected")


def test_validate_transaction_list():
    transactions = [
        valid_transaction(),
        {
            "date": "invalid-date",
            "description": "",
            "debit": "invalid",
            "credit": None,
            "balance": None,
        }
    ]

    result = validate_transactions(transactions)

    assert result["success"] is True
    assert result["total_transactions"] == 2
    assert result["valid_count"] == 1
    assert result["invalid_count"] == 1

    print("PASS: Transaction list separated")


def test_invalid_input():
    result = validate_transaction("not a dictionary")

    assert result["valid"] is False

    result = validate_transactions("not a list")

    assert result["success"] is False

    print("PASS: Invalid inputs handled")


if __name__ == "__main__":
    test_valid_date()
    test_valid_amount()
    test_valid_transaction()
    test_missing_required_fields()
    test_debit_and_credit_both_positive()
    test_negative_debit_rejected()
    test_validate_transaction_list()
    test_invalid_input()

    print("\nAll data validator tests passed!")