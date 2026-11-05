from datetime import datetime
from decimal import Decimal, InvalidOperation


def normalize_date(date_value):
    """Convert supported date values to YYYY-MM-DD."""

    if not date_value:
        return None

    if isinstance(date_value, datetime):
        return date_value.strftime("%Y-%m-%d")

    date_text = str(date_value).strip()

    supported_formats = [
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%d-%m-%y",
        "%d/%m/%y",
    ]

    for date_format in supported_formats:
        try:
            parsed_date = datetime.strptime(date_text, date_format)
            return parsed_date.strftime("%Y-%m-%d")
        except ValueError:
            continue

    return None


def normalize_amount(amount_value):
    """Convert an amount to a rounded float, or None if unavailable."""

    if amount_value is None or amount_value == "":
        return None

    try:
        amount_text = str(amount_value).strip()

        # Remove common currency symbols and separators
        amount_text = (
            amount_text
            .replace(",", "")
            .replace("₹", "")
            .replace("Rs.", "")
            .strip()
        )

        # Support accounting-style negative amounts: (250.00)
        if amount_text.startswith("(") and amount_text.endswith(")"):
            amount_text = "-" + amount_text[1:-1]

        amount = Decimal(amount_text)

        # Financial amounts are rounded to two decimal places
        return float(amount.quantize(Decimal("0.01")))

    except (InvalidOperation, ValueError):
        return None


def normalize_description(description):
    """Clean and standardize a transaction description."""

    if description is None:
        return ""

    description = str(description)

    # Replace tabs and repeated whitespace with single spaces
    description = " ".join(description.split())

    return description.strip()


def normalize_transaction(transaction):
    """Normalize one transaction dictionary."""

    if not isinstance(transaction, dict):
        return {
            "success": False,
            "transaction": None,
            "error": "Transaction must be a dictionary."
        }

    normalized_transaction = {
        "date": normalize_date(transaction.get("date")),
        "description": normalize_description(
            transaction.get("description")
        ),
        "debit": normalize_amount(transaction.get("debit")),
        "credit": normalize_amount(transaction.get("credit")),
        "balance": normalize_amount(transaction.get("balance")),
    }

    return {
        "success": True,
        "transaction": normalized_transaction,
        "error": None
    }


def normalize_transactions(transactions):
    """Normalize a list of transaction dictionaries."""

    if not isinstance(transactions, list):
        return {
            "success": False,
            "transactions": [],
            "total_transactions": 0,
            "error": "Input must be a list."
        }

    normalized_transactions = []

    for transaction in transactions:
        result = normalize_transaction(transaction)

        if result["success"]:
            normalized_transactions.append(result["transaction"])

    return {
        "success": True,
        "transactions": normalized_transactions,
        "total_transactions": len(normalized_transactions),
        "error": None
    }