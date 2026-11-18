
from decimal import Decimal, InvalidOperation


def to_decimal(value):
    """Safely convert an amount into Decimal."""

    if value is None or value == "":
        return Decimal("0")

    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError(f"Invalid transaction amount: {value}")


def classify_transaction(
    description,
    debit=0,
    credit=0,
    normalized_merchant=None
):
    """
    Classify a transaction using deterministic rules.

    Transaction types:
    income, expense, transfer, refund, other
    """

    if not isinstance(description, str) or not description.strip():
        return {
            "success": False,
            "transaction_type": "other",
            "category": "Uncategorized",
            "confidence_score": Decimal("0.0000"),
            "reason": "Missing transaction description."
        }

    try:
        debit_amount = to_decimal(debit)
        credit_amount = to_decimal(credit)
    except ValueError as error:
        return {
            "success": False,
            "transaction_type": "other",
            "category": "Uncategorized",
            "confidence_score": Decimal("0.0000"),
            "reason": str(error)
        }

    if debit_amount < 0 or credit_amount < 0:
        return {
            "success": False,
            "transaction_type": "other",
            "category": "Uncategorized",
            "confidence_score": Decimal("0.0000"),
            "reason": "Negative debit or credit amount."
        }

    if debit_amount > 0 and credit_amount > 0:
        return {
            "success": False,
            "transaction_type": "other",
            "category": "Uncategorized",
            "confidence_score": Decimal("0.0000"),
            "reason": "Both debit and credit are positive."
        }

    text = description.upper()

    # 1. Internal transfer
    transfer_keywords = [
        "TRF TO SELF",
        "TRANSFER TO OWN",
        "OWN ACCOUNT TRANSFER",
        "SELF TRANSFER",
        "TRF FROM SELF",
        "TRANSFER FROM OWN"
    ]

    if any(keyword in text for keyword in transfer_keywords):
        return {
            "success": True,
            "transaction_type": "transfer",
            "category": "Internal Transfer",
            "confidence_score": Decimal("0.9500"),
            "reason": "Description contains an own-account transfer indicator."
        }

    # 2. Refund
    refund_keywords = [
        "REFUND",
        "REVERSAL",
        "CASHBACK",
        "PURCHASE RETURN"
    ]

    if credit_amount > 0 and any(
        keyword in text for keyword in refund_keywords
    ):
        return {
            "success": True,
            "transaction_type": "refund",
            "category": "Refund",
            "confidence_score": Decimal("0.9000"),
            "reason": "Credit transaction contains a refund or reversal indicator."
        }

    # 3. Income
    income_keywords = [
        "SALARY",
        "INTEREST CREDIT",
        "DIVIDEND",
        "PENSION",
        "FREELANCE PAYMENT"
    ]

    if credit_amount > 0 and any(
        keyword in text for keyword in income_keywords
    ):
        return {
            "success": True,
            "transaction_type": "income",
            "category": "Income",
            "confidence_score": Decimal("0.9500"),
            "reason": "Credit transaction contains an income indicator."
        }

    # 4. Expense
    if debit_amount > 0:

        if any(word in text for word in ["LOAN EMI", "EMI"]):
            category = "Loan Payment"

        elif "ATM CASH WDL" in text:
            category = "Cash Withdrawal"

        elif any(word in text for word in [
            "GROCERY", "FRESHBASKET", "FRESH BASKET"
        ]):
            category = "Groceries"

        elif any(word in text for word in [
            "RESTAURANT", "FOOD", "DINNER", "LUNCH"
        ]):
            category = "Food"

        elif any(word in text for word in [
            "ELECTRICITY", "BROADBAND", "BILLPAY"
        ]):
            category = "Utilities"

        elif any(word in text for word in [
            "RENT", "HOUSING"
        ]):
            category = "Housing"

        else:
            category = "Uncategorized"

        return {
            "success": True,
            "transaction_type": "expense",
            "category": category,
            "confidence_score": Decimal("0.8500")
                if category != "Uncategorized"
                else Decimal("0.5000"),
            "reason": "Transaction has a debit amount."
        }

    # 5. Other / unknown
    return {
        "success": True,
        "transaction_type": "other",
        "category": "Uncategorized",
        "confidence_score": Decimal("0.3000"),
        "reason": "No reliable classification rule matched."
    }
