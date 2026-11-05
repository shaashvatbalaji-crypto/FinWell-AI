from preprocessing.transaction_parser import parse_transactions


def test_parse_three_amount_columns():
    text = """
    Date Description Debit Credit Balance
    01-11-2026 Grocery Store 250.00 0.00 4750.00
    02-11-2026 Monthly Salary 0.00 25000.00 29750.00
    """

    result = parse_transactions(text)

    assert result["success"] is True
    assert result["total_transactions"] == 2

    first = result["transactions"][0]

    assert first["date"] == "2026-11-01"
    assert first["description"] == "Grocery Store"
    assert first["debit"] == 250.00
    assert first["credit"] == 0.00
    assert first["balance"] == 4750.00

    second = result["transactions"][1]

    assert second["description"] == "Monthly Salary"
    assert second["debit"] == 0.00
    assert second["credit"] == 25000.00

    print("PASS: Three amount columns parsed")


def test_parse_slash_date():
    text = "03/11/2026 Electricity Bill 1800.00 0.00 27950.00"

    result = parse_transactions(text)

    assert result["success"] is True
    assert result["total_transactions"] == 1
    assert result["transactions"][0]["date"] == "2026-11-03"

    print("PASS: Slash date parsed")


def test_skip_non_transaction_lines():
    text = """
    BANK STATEMENT
    Account Number: 123456
    Date Description Debit Credit Balance
    01-11-2026 Grocery Store 250.00 0.00 4750.00
    """

    result = parse_transactions(text)

    assert result["success"] is True
    assert result["total_transactions"] == 1

    print("PASS: Non-transaction lines skipped")


def test_empty_input():
    result = parse_transactions("")

    assert result["success"] is False
    assert result["transactions"] == []

    print("PASS: Empty input handled")


def test_non_string_input():
    result = parse_transactions(None)

    assert result["success"] is False
    assert result["transactions"] == []

    print("PASS: Non-string input handled")


if __name__ == "__main__":
    test_parse_three_amount_columns()
    test_parse_slash_date()
    test_skip_non_transaction_lines()
    test_empty_input()
    test_non_string_input()

    print("\nAll transaction parser tests passed!")