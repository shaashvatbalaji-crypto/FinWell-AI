
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from reconciliation.reference_extractor import (
    extract_reference,
    normalize_reference,
)


def _money(value):
    if value is None or value == "":
        return Decimal("0.00")

    try:
        amount = Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError(f"Invalid amount: {value}")

    if not amount.is_finite():
        raise ValueError(f"Invalid amount: {value}")

    return amount.quantize(Decimal("0.01"))


def _date(value):
    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    if not value:
        raise ValueError("Transaction date is missing.")

    text = str(value).strip()

    for fmt in (
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%d-%b-%Y",
        "%d-%b-%y",
    ):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue

    raise ValueError(f"Unsupported date: {value}")


def _reference(transaction):
    explicit = (
        transaction.get("settlement_reference")
        or transaction.get("batch_reference")
        or transaction.get("reference")
    )

    if explicit:
        return normalize_reference(explicit)

    return extract_reference(
        transaction.get("description", "")
    )


def _currency(transaction):
    value = (
        transaction.get("currency")
        or transaction.get("currency_code")
    )

    return str(value).strip().upper() if value else None


def _user_id(transaction):
    return transaction.get("user_id")


def _transaction_id(transaction):
    return transaction.get("transaction_id")


def _gateway_profile(transaction):
    """
    Gateway transaction:
    - positive gross amount
    - user_id
    - transaction date
    - currency
    - optional processing_fee
    - optional settlement_reference / batch_reference
    """

    amount = _money(
        transaction.get("gross_amount")
        if transaction.get("gross_amount") is not None
        else transaction.get("amount")
        if transaction.get("amount") is not None
        else transaction.get("credit")
    )

    fee = _money(
        transaction.get("processing_fee")
        if transaction.get("processing_fee") is not None
        else transaction.get("fee_amount")
    )

    if amount <= 0:
        raise ValueError("Gateway gross amount must be positive.")

    if fee < 0 or fee > amount:
        raise ValueError("Invalid gateway processing fee.")

    user_id = _user_id(transaction)
    currency = _currency(transaction)
    transaction_date = _date(
        transaction.get("transaction_date")
        or transaction.get("date")
    )

    if not isinstance(user_id, int) or isinstance(user_id, bool) or user_id <= 0:
        raise ValueError("A valid gateway user_id is required.")

    if not currency:
        raise ValueError("Gateway currency is required.")

    return {
        "transaction_id": _transaction_id(transaction),
        "user_id": user_id,
        "date": transaction_date,
        "gross": amount,
        "fee": fee,
        "net": amount - fee,
        "currency": currency,
        "reference": _reference(transaction),
        "description": str(transaction.get("description") or ""),
    }


def _bank_profile(transaction):
    """Bank settlement must be represented by a positive credit."""

    credit = _money(transaction.get("credit"))

    if credit <= 0:
        raise ValueError("Bank settlement must have a positive credit.")

    user_id = _user_id(transaction)
    currency = _currency(transaction)
    transaction_date = _date(
        transaction.get("transaction_date")
        or transaction.get("date")
    )

    if not isinstance(user_id, int) or isinstance(user_id, bool) or user_id <= 0:
        raise ValueError("A valid bank transaction user_id is required.")

    if not currency:
        raise ValueError("Bank transaction currency is required.")

    return {
        "transaction_id": _transaction_id(transaction),
        "user_id": user_id,
        "date": transaction_date,
        "net": credit,
        "currency": currency,
        "reference": _reference(transaction),
        "description": str(transaction.get("description") or ""),
    }


def _settlement_group_key(profile):
    """
    Group gateway payments only when they share an explicit
    settlement or batch reference.
    """

    return profile["reference"]


def reconcile_settlements(
    gateway_transactions,
    bank_transactions,
    max_date_gap_days=5,
):
    """
    Propose gateway-to-bank settlement matches in memory.

    Supported:
      - One gateway payment -> one bank credit.
      - Multiple gateway payments -> one bank credit,
        when all share an explicit settlement reference.

    Gateway transaction fields:
      user_id, transaction_id, date/transaction_date,
      amount/gross_amount/credit, currency,
      processing_fee (optional), settlement_reference (optional).

    Bank transaction fields:
      user_id, transaction_id, date/transaction_date,
      credit, currency, settlement_reference/reference.

    No database or ChromaDB writes are performed.
    Original input dictionaries are never modified.
    """

    result = {
        "success": True,
        "mode": "dry_run",
        "writes_performed": False,
        "gateway_count": len(gateway_transactions or []),
        "bank_count": len(bank_transactions or []),
        "candidate_count": 0,
        "matched_candidates": [],
        "review_required": [],
        "unmatched_gateway": [],
        "unmatched_bank": [],
        "invalid_transactions": [],
        "total_gross": Decimal("0.00"),
        "total_fees": Decimal("0.00"),
        "total_expected_net": Decimal("0.00"),
        "total_matched_net": Decimal("0.00"),
    }

    if (
        isinstance(max_date_gap_days, bool)
        or not isinstance(max_date_gap_days, int)
        or max_date_gap_days < 0
    ):
        result["success"] = False
        result["message"] = "max_date_gap_days must be a non-negative integer."
        return result

    gateway_profiles = []
    bank_profiles = []

    for index, transaction in enumerate(gateway_transactions or []):
        try:
            profile = _gateway_profile(transaction)
            profile["input_index"] = index
            gateway_profiles.append(profile)
        except (ValueError, TypeError) as error:
            result["invalid_transactions"].append({
                "source": "gateway",
                "input_index": index,
                "transaction_id": _transaction_id(transaction),
                "reason": str(error),
            })

    for index, transaction in enumerate(bank_transactions or []):
        try:
            profile = _bank_profile(transaction)
            profile["input_index"] = index
            bank_profiles.append(profile)
        except (ValueError, TypeError) as error:
            result["invalid_transactions"].append({
                "source": "bank",
                "input_index": index,
                "transaction_id": _transaction_id(transaction),
                "reason": str(error),
            })

    result["total_gross"] = sum(
        (item["gross"] for item in gateway_profiles),
        Decimal("0.00")
    )

    result["total_fees"] = sum(
        (item["fee"] for item in gateway_profiles),
        Decimal("0.00")
    )

    result["total_expected_net"] = sum(
        (item["net"] for item in gateway_profiles),
        Decimal("0.00")
    )

    used_gateway = set()
    used_bank = set()

    # Group only by explicit gateway settlement references.
    groups = {}

    for profile in gateway_profiles:
        reference = _settlement_group_key(profile)

        if reference:
            key = (profile["user_id"], profile["currency"], reference)
        else:
            # Missing references remain individual candidates.
            key = (
                profile["user_id"],
                profile["currency"],
                "__SINGLE__",
                profile["input_index"],
            )

        groups.setdefault(key, []).append(profile)

    for group_key, group in groups.items():
        first = group[0]

        # A shared reference is required for multi-payment groups.
        if len(group) > 1 and not first["reference"]:
            continue

        expected_net = sum(
            (item["net"] for item in group),
            Decimal("0.00")
        )

        group_date = max(item["date"] for item in group)
        group_ids = {item["input_index"] for item in group}

        possible_banks = []

        for bank in bank_profiles:
            if bank["input_index"] in used_bank:
                continue

            if bank["user_id"] != first["user_id"]:
                continue

            if bank["currency"] != first["currency"]:
                continue

            date_gap = abs((bank["date"] - group_date).days)

            if date_gap > max_date_gap_days:
                continue

            if (
                first["reference"]
                and bank["reference"]
                and first["reference"] != bank["reference"]
            ):
                continue

            if bank["net"] == expected_net:
                possible_banks.append(bank)

        # A match needs exactly one bank candidate.
        if len(possible_banks) == 1:
            bank = possible_banks[0]

            candidate = {
                "status": "proposed",
                "confidence_label": (
                    "high"
                    if first["reference"]
                    and bank["reference"] == first["reference"]
                    else "medium"
                ),
                "gateway_transaction_ids": [
                    item["transaction_id"] for item in group
                ],
                "bank_transaction_id": bank["transaction_id"],
                "user_id": first["user_id"],
                "currency": first["currency"],
                "gross_amount": sum(
                    (item["gross"] for item in group),
                    Decimal("0.00")
                ),
                "processing_fee": sum(
                    (item["fee"] for item in group),
                    Decimal("0.00")
                ),
                "expected_net": expected_net,
                "bank_credit": bank["net"],
                "reference": first["reference"],
                "date_gap_days": abs(
                    (bank["date"] - group_date).days
                ),
            }

            result["matched_candidates"].append(candidate)
            used_gateway.update(group_ids)
            used_bank.add(bank["input_index"])
            result["total_matched_net"] += expected_net

        elif len(possible_banks) > 1:
            result["review_required"].append({
                "reason": "Multiple bank credits match the settlement group.",
                "gateway_transaction_ids": [
                    item["transaction_id"] for item in group
                ],
                "possible_bank_transaction_ids": [
                    item["transaction_id"]
                    for item in possible_banks
                ],
                "expected_net": expected_net,
                "reference": first["reference"],
            })

    # Report gateway records not included in a confirmed proposal.
    for profile in gateway_profiles:
        if profile["input_index"] not in used_gateway:
            result["unmatched_gateway"].append({
                "transaction_id": profile["transaction_id"],
                "reference": profile["reference"],
                "expected_net": profile["net"],
            })

    for profile in bank_profiles:
        if profile["input_index"] not in used_bank:
            result["unmatched_bank"].append({
                "transaction_id": profile["transaction_id"],
                "reference": profile["reference"],
                "credit": profile["net"],
            })

    result["candidate_count"] = len(result["matched_candidates"])
    result["review_count"] = len(result["review_required"])

    return result
