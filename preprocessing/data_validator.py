from datetime import datetime
from decimal import Decimal, InvalidOperation


REQUIRED_FIELDS = ["date", "description"]


def validate_date(date_value) -> bool:
    """Return True if date is a valid YYYY-MM-DD value."""

    if not isinstance(date_value, str):
        return False

    try:
        datetime.strptime(date_value, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def validate_amount(amount_value) -> bool:
    """Return True if amount is numeric and finite, or None."""

    if amount_value is None:
        return True

    try:
        amount = Decimal(str(amount_value))
        return amount.is_finite()
    except (InvalidOperation, ValueError):
        return False


def validate_transaction(transaction: dict) -> dict:
    """Validate one normalized transaction."""

    if not isinstance(transaction, dict):
        return {
            "valid": False,
            "errors": ["Transaction must be a dictionary."]
        }

    errors = []

    # Required fields
    for field in REQUIRED_FIELDS:
        if transaction.get(field) is None or str(transaction.get(field)).strip() == "":
            errors.append(f"Missing required field: {field}")

    # Date format
    if transaction.get("date") and not validate_date(transaction["date"]):
        errors.append("Date must use YYYY-MM-DD format and be a valid date.")

    # Description
    description = transaction.get("description")

    if description is not None and not isinstance(description, str):
        errors.append("Description must be a string.")

    # Amount fields
    amount_fields = ["debit", "credit", "balance"]

    for field in amount_fields:
        value = transaction.get(field)

        if not validate_amount(value):
            errors.append(f"{field} must be a valid finite number.")

    # Debit and credit should not both be positive
    debit = transaction.get("debit")
    credit = transaction.get("credit")

    if validate_amount(debit) and validate_amount(credit):
        if debit is not None and credit is not None:
            if debit > 0 and credit > 0:
                errors.append(
                    "Debit and credit cannot both be positive "
                    "for the same transaction."
                )

    # Debit and credit should not be negative
    for field in ["debit", "credit"]:
        value = transaction.get(field)

        if validate_amount(value) and value is not None and value < 0:
            errors.append(f"{field} cannot be negative.")

    return {
        "valid": len(errors) == 0,
        "errors": errors
    }


def validate_transactions(transactions: list) -> dict:
    """Validate a list of transactions and separate valid/invalid records."""

    if not isinstance(transactions, list):
        return {
            "success": False,
            "valid_transactions": [],
            "invalid_transactions": [],
            "total_transactions": 0,
            "error": "Input must be a list."
        }

    valid_transactions = []
    invalid_transactions = []

    for index, transaction in enumerate(transactions):
        result = validate_transaction(transaction)

        if result["valid"]:
            valid_transactions.append(transaction)
        else:
            invalid_transactions.append({
                "index": index,
                "transaction": transaction,
                "errors": result["errors"]
            })

    return {
        "success": True,
        "valid_transactions": valid_transactions,
        "invalid_transactions": invalid_transactions,
        "total_transactions": len(transactions),
        "valid_count": len(valid_transactions),
        "invalid_count": len(invalid_transactions),
        "error": None
    }