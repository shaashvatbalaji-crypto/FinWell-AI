
"""
FinWell AI - Inter Account Reconciler

Matches transfers between a user's own accounts.

Matching rules:
1. Different account IDs.
2. Opposite directions: debit <-> credit.
3. Equal amounts.
4. Dates within the configured tolerance.
5. Prefer exact transfer reference matches.
6. Without references, require transfer-related descriptions.

An amount-only match is never accepted.
"""

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from itertools import combinations


TRANSFER_KEYWORDS = (
    "TRANSFER",
    "TRF",
    "FUND TRANSFER",
    "SELF TRANSFER",
    "OWN ACCOUNT",
    "TO SELF",
    "FROM SELF",
    "NEFT",
    "RTGS",
    "IMPS",
    "INTERNAL TRANSFER",
)

REFERENCE_PATTERN = re.compile(
    r"\b(?:TRF|UTR|REF|IMPS|NEFT|RTGS|UPI)[\s:/#-]*"
    r"([A-Z0-9]{4,})\b",
    re.IGNORECASE,
)


def _to_decimal(value):
    """Safely convert an amount into Decimal."""
    if value is None or value == "":
        return Decimal("0.00")

    try:
        amount = Decimal(str(value).replace(",", "").replace("₹", "").strip())

        if not amount.is_finite():
            raise ValueError("Amount must be finite.")

        return amount.quantize(Decimal("0.01"))

    except (InvalidOperation, ValueError):
        raise ValueError(f"Invalid transaction amount: {value!r}")


def _get_date(transaction):
    """Read either the normalized date or MySQL transaction_date."""
    value = transaction.get("date") or transaction.get("transaction_date")

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    if value is None:
        return None

    text = str(value).strip()

    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue

    return None


def _get_description(transaction):
    return " ".join(
        str(transaction.get("description") or "").upper().split()
    )


def _get_reference(description):
    """
    Extract an explicit transaction reference without mistaking UPI/IMPS
    narration words (for example, "UPI TRANSFER" or "UPI RECEIVED")
    for reference values.

    Priority:
      1. A value explicitly introduced by REF / REFERENCE.
      2. A standalone TRF/UTR-style identifier such as TRF601.
      3. Other compact alphanumeric IDs containing digits.

    We deliberately do not treat the words immediately following UPI or
    IMPS as references because they are commonly transaction descriptors.
    """
    text = " ".join(str(description or "").upper().split())

    # Explicit reference marker: REF TRF601, REF: ABC123, etc.
    match = re.search(
        r"\b(?:REF|REFERENCE)\s*[:/#-]?\s*"
        r"([A-Z0-9][A-Z0-9-]{2,})\b",
        text,
    )
    if match:
        return match.group(1).replace("-", "").upper()

    # Explicit transfer identifiers, including compact and separated forms.
    match = re.search(
        r"\b(TRF|UTR)\s*[-:/#]?\s*([A-Z0-9]{3,})\b",
        text,
    )
    if match:
        return (match.group(1) + match.group(2)).upper()

    # Generic compact IDs containing both letters and digits.
    match = re.search(
        r"\b([A-Z]{2,8}\d{3,})\b",
        text,
    )
    return match.group(1).upper() if match else None


def _get_direction_and_amount(transaction):
    """
    Return:
        ("debit", amount)
        ("credit", amount)
        (None, 0)
    """
    debit = _to_decimal(transaction.get("debit"))
    credit = _to_decimal(transaction.get("credit"))

    if debit > 0 and credit > 0:
        raise ValueError(
            "A transaction cannot have both debit and credit amounts."
        )

    if debit > 0:
        return "debit", debit

    if credit > 0:
        return "credit", credit

    return None, Decimal("0.00")


def _is_transfer_description(description):
    return any(
        keyword in description
        for keyword in TRANSFER_KEYWORDS
    )


def _transaction_identity(transaction, index):
    """
    Prefer database transaction_id.

    For in-memory normalized transactions, use a stable
    identity based on account, document, index and content.
    """
    transaction_id = transaction.get("transaction_id")

    if transaction_id is not None:
        return str(transaction_id)

    return (
        f"{transaction.get('account_id')}|"
        f"{transaction.get('document_id')}|"
        f"{index}"
    )


def _prepare_transaction(transaction, index):
    if not isinstance(transaction, dict):
        raise ValueError(
            f"Transaction at index {index} must be a dictionary."
        )

    account_id = transaction.get("account_id")

    if account_id is None:
        raise ValueError(
            f"Transaction at index {index} has no account_id."
        )

    transaction_date = _get_date(transaction)

    if transaction_date is None:
        raise ValueError(
            f"Transaction at index {index} has an invalid or missing date."
        )

    description = _get_description(transaction)
    direction, amount = _get_direction_and_amount(transaction)

    return {
        "index": index,
        "identity": _transaction_identity(transaction, index),
        "account_id": account_id,
        "date": transaction_date,
        "description": description,
        "reference": _get_reference(description),
        "direction": direction,
        "amount": amount,
        "currency": str(transaction.get("currency") or "INR").upper(),
        "original": transaction,
    }


def _evaluate_pair(left, right, date_tolerance_days):
    """Return a match score, or None if the pair is not eligible."""

    if left["account_id"] == right["account_id"]:
        return None

    if left["currency"] != right["currency"]:
        return None

    if left["direction"] is None or right["direction"] is None:
        return None

    if left["direction"] == right["direction"]:
        return None

    if left["amount"] != right["amount"]:
        return None

    date_difference = abs((left["date"] - right["date"]).days)

    if date_difference > date_tolerance_days:
        return None

    left_ref = left["reference"]
    right_ref = right["reference"]

    # Both sides contain references: they must agree.
    if left_ref and right_ref:
        if left_ref != right_ref:
            return None

        return 100 + (date_tolerance_days - date_difference)

    # Do not match when only one side has a reference.
    if bool(left_ref) != bool(right_ref):
        return None

    # Without references, require transfer-like descriptions
    # on both sides.
    if not (
        _is_transfer_description(left["description"])
        and _is_transfer_description(right["description"])
    ):
        return None

    return 50 + (date_tolerance_days - date_difference)


def match_inter_account_transfers(
    transactions,
    date_tolerance_days=2,
):
    """
    Match internal transfers across accounts.

    Args:
        transactions: List of transaction dictionaries.
        date_tolerance_days: Maximum allowed date difference.

    Returns:
        {
            "success": True,
            "matches": [...],
            "unmatched_transactions": [...],
            "ambiguous_transactions": [...],
            "summary": {...}
        }
    """

    if not isinstance(transactions, list):
        raise TypeError("transactions must be a list.")

    if date_tolerance_days < 0:
        raise ValueError("date_tolerance_days cannot be negative.")

    prepared = [
        _prepare_transaction(transaction, index)
        for index, transaction in enumerate(transactions)
    ]

    candidates = []

    for left, right in combinations(prepared, 2):
        score = _evaluate_pair(
            left,
            right,
            date_tolerance_days,
        )

        if score is not None:
            candidates.append({
                "left": left,
                "right": right,
                "score": score,
            })

    # Only accept an unambiguous best match for both transactions.
    by_transaction = {}

    for candidate in candidates:
        for item in (candidate["left"], candidate["right"]):
            by_transaction.setdefault(item["index"], []).append(candidate)

    accepted_pairs = []
    ambiguous_indices = set()

    for candidate in candidates:
        left = candidate["left"]
        right = candidate["right"]
        score = candidate["score"]

        def unique_best(item, other):
            options = by_transaction[item["index"]]
            best_score = max(option["score"] for option in options)
            best = [
                option for option in options
                if option["score"] == best_score
            ]

            return (
                best_score == score
                and len(best) == 1
                and other["index"] in (
                    best[0]["left"]["index"],
                    best[0]["right"]["index"],
                )
            )

        if unique_best(left, right) and unique_best(right, left):
            accepted_pairs.append(candidate)
        else:
            ambiguous_indices.update((left["index"], right["index"]))

    matched_indices = set()
    matches = []

    for pair_number, candidate in enumerate(
        accepted_pairs,
        start=1,
    ):
        left = candidate["left"]
        right = candidate["right"]

        # Defensive protection against a transaction being used twice.
        if (
            left["index"] in matched_indices
            or right["index"] in matched_indices
        ):
            continue

        matched_indices.update((left["index"], right["index"]))

        debit_side = (
            left if left["direction"] == "debit" else right
        )
        credit_side = (
            left if left["direction"] == "credit" else right
        )

        matches.append({
            "match_id": f"TRANSFER-{pair_number:04d}",
            "reference": (
                left["reference"] or right["reference"]
            ),
            "amount": float(left["amount"]),
            "currency": left["currency"],
            "date_difference_days": abs(
                (left["date"] - right["date"]).days
            ),
            "debit_account_id": debit_side["account_id"],
            "credit_account_id": credit_side["account_id"],
            "debit_transaction_id": debit_side["identity"],
            "credit_transaction_id": credit_side["identity"],
            "debit_transaction": debit_side["original"],
            "credit_transaction": credit_side["original"],
            "matching_score": candidate["score"],
        })

    unmatched = [
        item["original"]
        for item in prepared
        if item["index"] not in matched_indices
    ]

    ambiguous = [
        item["original"]
        for item in prepared
        if (
            item["index"] not in matched_indices
            and item["index"] in ambiguous_indices
        )
    ]

    return {
        "success": True,
        "matches": matches,
        "unmatched_transactions": unmatched,
        "ambiguous_transactions": ambiguous,
        "summary": {
            "total_transactions": len(transactions),
            "matched_transfer_pairs": len(matches),
            "matched_transaction_count": len(matched_indices),
            "unmatched_transaction_count": len(unmatched),
            "ambiguous_transaction_count": len(ambiguous),
            "internal_transfer_amount": round(
                sum(match["amount"] for match in matches),
                2,
            ),
        },
    }
