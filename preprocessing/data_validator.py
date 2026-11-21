"""Strict transaction validation for FinWell AI."""
from datetime import datetime
from decimal import Decimal, InvalidOperation

CENT = Decimal("0.01")


def _decimal(value, field):
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    if isinstance(value, bool):
        raise ValueError(f"{field} cannot be boolean")
    try:
        result = Decimal(str(value))
        if not result.is_finite():
            raise ValueError(f"{field} must be finite")
        return result.quantize(CENT)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field} is not a valid monetary amount") from exc


def validate_transaction(transaction):
    errors = []
    if not isinstance(transaction, dict):
        return False, ["Transaction must be a dictionary."]

    raw_date = transaction.get("date")
    try:
        datetime.strptime(str(raw_date), "%Y-%m-%d")
    except (TypeError, ValueError):
        errors.append("date must be a valid YYYY-MM-DD date.")

    if not isinstance(transaction.get("description"), str) or not transaction["description"].strip():
        errors.append("description is required.")

    values = {}
    for field in ("debit", "credit", "balance"):
        try:
            values[field] = _decimal(transaction.get(field), field)
        except ValueError as exc:
            errors.append(str(exc))
            values[field] = None

    debit, credit = values["debit"], values["credit"]
    if debit is not None and debit < 0:
        errors.append("debit cannot be negative; use a positive debit amount.")
    if credit is not None and credit < 0:
        errors.append("credit cannot be negative; use a positive credit amount.")
    if debit is not None and credit is not None and debit > 0 and credit > 0:
        errors.append("Both debit and credit are positive; direction is ambiguous.")
    if (debit is None or debit == 0) and (credit is None or credit == 0):
        errors.append("A transaction must have exactly one positive debit or credit amount.")
    if transaction.get("direction_uncertain"):
        errors.append("Transaction direction could not be established; manual review required.")

    return not errors, errors


def validate_transactions(transactions):
    if not isinstance(transactions, list):
        return {"success": False, "valid_transactions": [],
                "invalid_transactions": [], "total": 0,
                "valid_count": 0, "invalid_count": 0,
                "errors": ["Input must be a list."]}

    valid, invalid = [], []
    for index, transaction in enumerate(transactions):
        ok, errors = validate_transaction(transaction)
        if ok:
            clean = dict(transaction)
            clean.pop("direction_uncertain", None)
            valid.append(clean)
        else:
            invalid.append({"index": index, "transaction": transaction, "errors": errors})

    return {"success": len(invalid) == 0, "valid_transactions": valid,
            "invalid_transactions": invalid, "total": len(transactions),
            "valid_count": len(valid), "invalid_count": len(invalid),
            "errors": [f"Row {x['index'] + 1}: {e}"
                       for x in invalid for e in x["errors"]]}
