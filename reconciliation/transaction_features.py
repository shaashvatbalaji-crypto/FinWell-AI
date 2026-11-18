
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from reconciliation.reference_extractor import (
    extract_reference,
    normalize_reference,
)

from reconciliation.merchant_normalizer import (
    normalize_merchant,
    normalize_text,
)


def normalize_transaction_date(value):
    """Convert supported date values into datetime.date."""

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    if not value:
        raise ValueError("Transaction date is missing.")

    text = str(value).strip()

    formats = (
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%d-%m-%y",
        "%d/%m/%y",
        "%d-%b-%Y",
        "%d-%b-%y",
    )

    for fmt in formats:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue

    raise ValueError(f"Unsupported transaction date: {value}")


def normalize_money(value):
    """Convert an amount into a two-decimal-place Decimal."""

    if value is None or value == "":
        return Decimal("0.00")

    try:
        amount = Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, ValueError):
        raise ValueError(f"Invalid transaction amount: {value}")

    if not amount.is_finite():
        raise ValueError(f"Invalid transaction amount: {value}")

    return amount.quantize(Decimal("0.01"))


def normalize_account_id(value):
    if value is None:
        return None

    value = str(value).strip()

    return value or None


def normalize_currency(value):
    if value is None:
        return None

    value = str(value).strip().upper()

    return value or None


def extract_transaction_features(
    transaction,
    merchant_aliases=None,
    reference_labels=None,
):
    """
    Extract standardized features without modifying
    the original transaction dictionary.
    """

    if not isinstance(transaction, dict):
        raise TypeError("Transaction must be a dictionary.")

    description = transaction.get("description") or ""

    debit = normalize_money(transaction.get("debit"))
    credit = normalize_money(transaction.get("credit"))

    if debit < 0 or credit < 0:
        raise ValueError("Debit and credit must not be negative.")

    if debit > 0 and credit > 0:
        raise ValueError(
            "Both debit and credit cannot be positive."
        )

    if debit > 0:
        amount = debit
        direction = "debit"

    elif credit > 0:
        amount = credit
        direction = "credit"

    else:
        amount = Decimal("0.00")
        direction = "zero"

    reference = extract_reference(
        description,
        custom_labels=reference_labels,
    )

    return {
        "transaction_id": transaction.get("transaction_id"),
        "user_id": transaction.get("user_id"),
        "document_id": transaction.get("document_id"),
        "account_id": normalize_account_id(
            transaction.get("account_id")
        ),
        "transaction_date": normalize_transaction_date(
            transaction.get("transaction_date")
            or transaction.get("date")
        ),
        "description": str(description),
        "normalized_description": normalize_text(description),
        "merchant": normalize_merchant(
            description,
            merchant_aliases=merchant_aliases,
        ),
        "reference": normalize_reference(reference),
        "debit": debit,
        "credit": credit,
        "amount": amount,
        "direction": direction,
        "currency": normalize_currency(
            transaction.get("currency")
            or transaction.get("currency_code")
        ),
    }
