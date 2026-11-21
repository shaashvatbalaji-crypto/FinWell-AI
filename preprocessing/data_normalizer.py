"""FinWell AI transaction normalization. Uses Decimal and reports row errors."""
import re
from datetime import datetime, date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

CENT = Decimal("0.01")
DATE_FORMATS = ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d-%m-%y", "%d/%m/%y")


def normalize_date(value):
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if not isinstance(value, str) or not value.strip():
        return None
    raw = value.strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def normalize_amount(value):
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    if isinstance(value, bool):
        raise ValueError("Boolean is not a valid amount")
    raw = str(value).strip()
    negative = raw.startswith("(") and raw.endswith(")")
    if negative:
        raw = raw[1:-1]
    raw = raw.replace(",", "").replace("₹", "").replace("â‚¹", "")
    raw = re.sub(r"^Rs\.?\s*", "", raw, flags=re.I).strip()
    try:
        amount = Decimal(raw)
        if not amount.is_finite():
            raise ValueError("Amount must be finite")
        if negative:
            amount = -amount
        return amount.quantize(CENT, rounding=ROUND_HALF_UP)
    except InvalidOperation as exc:
        raise ValueError(f"Invalid amount: {value!r}") from exc


def normalize_description(value):
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def normalize_transaction(transaction):
    if not isinstance(transaction, dict):
        return {"success": False, "transaction": None,
                "errors": ["Transaction must be a dictionary."]}
    errors = []
    normalized = dict(transaction)

    parsed_date = normalize_date(transaction.get("date"))
    if parsed_date is None:
        errors.append(f"Invalid or missing date: {transaction.get('date')!r}")
    normalized["date"] = parsed_date

    normalized["description"] = normalize_description(transaction.get("description"))
    if not normalized["description"]:
        errors.append("Missing transaction description.")

    for field in ("debit", "credit", "balance"):
        try:
            normalized[field] = normalize_amount(transaction.get(field))
        except ValueError as exc:
            errors.append(f"{field}: {exc}")
            normalized[field] = None

    # Preserve parser uncertainty for the validator.
    normalized["direction_uncertain"] = bool(transaction.get("direction_uncertain", False))
    return {"success": not errors, "transaction": normalized, "errors": errors}


def normalize_transactions(transactions):
    if not isinstance(transactions, list):
        return {"success": False, "transactions": [], "total_transactions": 0,
                "invalid_count": 0, "errors": ["Input must be a list."]}
    normalized, invalid, errors = [], [], []
    for index, transaction in enumerate(transactions):
        result = normalize_transaction(transaction)
        if result["transaction"] is not None:
            normalized.append(result["transaction"])
        if not result["success"]:
            invalid.append({"index": index, "transaction": transaction,
                            "errors": result["errors"]})
            errors.extend([f"Row {index + 1}: {e}" for e in result["errors"]])
    return {"success": len(invalid) == 0, "transactions": normalized,
            "total_transactions": len(normalized), "invalid_count": len(invalid),
            "invalid_transactions": invalid, "errors": errors}
