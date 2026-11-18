
"""Hackathon prototype: dry-run internal bank-transfer matching."""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Iterable

_CENT = Decimal("0.01")

_REFERENCE_PATTERNS = (
    re.compile(
        r"\b(?:UTR|REF(?:ERENCE)?|TXN\s*ID|RRN)\s*[:#-]?\s*"
        r"([A-Z0-9][A-Z0-9/-]{3,})\b",
        re.I,
    ),
    re.compile(r"\b(TRF\s*[-/]?\s*[A-Z0-9]{3,})\b", re.I),
)

_TRANSFER_TERMS = re.compile(
    r"\b(?:OWN\s*A/?C|OWN\s*ACCOUNT|SELF\s*TRANSFER|"
    r"TRANSFER\s*TO\s*OWN|TRANSFER\s*FROM\s*OWN|"
    r"TRF\s*TO\s*SELF|TRF\s*FROM\s*SELF)\b",
    re.I,
)


def _money(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None

    try:
        amount = Decimal(str(value).replace(",", "").strip())
        if not amount.is_finite():
            return None
        return amount.quantize(_CENT, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError):
        return None


def _date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        return None

    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        return None


def extract_reference(description: Any) -> str | None:
    """Extract a likely transaction reference without changing narration."""
    if not isinstance(description, str):
        return None

    text = " ".join(description.upper().split())

    for pattern in _REFERENCE_PATTERNS:
        match = pattern.search(text)
        if match:
            return re.sub(r"[^A-Z0-9]", "", match.group(1).upper())

    return None


def _profile(tx: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(tx, dict):
        return None

    debit = _money(tx.get("debit"))
    credit = _money(tx.get("credit"))

    debit_positive = debit is not None and debit > 0
    credit_positive = credit is not None and credit > 0

    # Exactly one positive debit/credit side is required.
    if debit_positive == credit_positive:
        return None

    amount = debit if debit_positive else credit
    tx_date = _date(tx.get("date"))
    description = tx.get("description")

    if (
        amount is None
        or tx_date is None
        or not isinstance(description, str)
        or not description.strip()
    ):
        return None

    if (
        tx.get("user_id") is None
        or tx.get("account_id") is None
        or tx.get("transaction_id") is None
    ):
        return None

    currency = tx.get("currency")
    currency = str(currency).strip().upper() if currency else None

    return {
        "transaction_id": tx["transaction_id"],
        "user_id": tx["user_id"],
        "account_id": tx["account_id"],
        "date": tx_date,
        "description": description.strip(),
        "direction": "debit" if debit_positive else "credit",
        "amount": amount,
        "reference": extract_reference(description),
        "currency": currency or None,
    }


def _account_record(
    accounts: Any,
    account_id: Any,
) -> dict[str, Any] | None:
    """Support either {account_id: metadata} or a list of metadata records."""
    if isinstance(accounts, dict):
        value = accounts.get(account_id)
        return value if isinstance(value, dict) else None

    if isinstance(accounts, (list, tuple)):
        for item in accounts:
            if (
                isinstance(item, dict)
                and item.get("account_id") == account_id
            ):
                return item

    return None


def _verified_owner(account: dict[str, Any] | None) -> Any:
    if not account or account.get("verified") is not True:
        return None
    return account.get("user_id")


def _review_item(
    profile: dict[str, Any],
    reason: str,
) -> dict[str, Any]:
    return {
        "transaction_id": profile["transaction_id"],
        "account_id": profile["account_id"],
        "date": profile["date"].isoformat(),
        "direction": profile["direction"],
        "amount": str(profile["amount"]),
        "currency": profile["currency"],
        "reference": profile["reference"],
        "status": "needs_review",
        "reason": reason,
    }


def reconcile_internal_transfers(
    transactions: Iterable[dict[str, Any]],
    accounts: dict[Any, dict[str, Any]] | list[dict[str, Any]],
    *,
    max_date_gap_days: int = 1,
) -> dict[str, Any]:
    """
    Find internal transfer candidates without writing to any database.

    A pair is proposed only when:
    - Both accounts have verified ownership by the same user.
    - The accounts are different.
    - Directions are opposite.
    - Amounts and known currencies match.
    - Dates are within the configured window.
    - Both references exist and match.
    - Both descriptions indicate an own-account transfer.

    Ambiguous matches are sent for review instead of selecting the first pair.
    """

    if (
        isinstance(max_date_gap_days, bool)
        or not isinstance(max_date_gap_days, int)
        or max_date_gap_days < 0
    ):
        raise ValueError("max_date_gap_days must be a non-negative integer")

    profiles: list[dict[str, Any]] = []
    invalid_transaction_ids: list[Any] = []
    seen_ids: set[Any] = set()

    for tx in transactions:
        profile = _profile(tx)
        tx_id = tx.get("transaction_id") if isinstance(tx, dict) else None

        if profile is None:
            invalid_transaction_ids.append(tx_id)
            continue

        try:
            if tx_id in seen_ids:
                invalid_transaction_ids.append(tx_id)
                continue
            seen_ids.add(tx_id)
        except TypeError:
            invalid_transaction_ids.append(tx_id)
            continue

        profiles.append(profile)

    legs: list[dict[str, Any]] = []
    review_required: list[dict[str, Any]] = []

    # Identify transfer-like transactions and verify account ownership.
    for profile in profiles:
        if not _TRANSFER_TERMS.search(profile["description"]):
            continue

        account = _account_record(accounts, profile["account_id"])
        owner = _verified_owner(account)

        if owner is None:
            review_required.append(
                _review_item(profile, "account_ownership_not_verified")
            )
            continue

        if owner != profile["user_id"]:
            review_required.append(
                _review_item(profile, "account_owner_does_not_match_transaction_user")
            )
            continue

        legs.append(profile)

    # First build all possible pairs. Do not greedily accept the first match.
    possible_pairs: list[dict[str, Any]] = []
    comparisons: list[dict[str, Any]] = []

    for i, left in enumerate(legs):
        for right in legs[i + 1:]:
            reasons: list[str] = []

            if left["user_id"] != right["user_id"]:
                reasons.append("different_users")

            if left["account_id"] == right["account_id"]:
                reasons.append("same_account")

            if left["direction"] == right["direction"]:
                reasons.append("directions_not_opposite")

            if left["amount"] != right["amount"]:
                reasons.append("amount_mismatch")

            if not left["currency"] or not right["currency"]:
                reasons.append("currency_unknown")
            elif left["currency"] != right["currency"]:
                reasons.append("currency_mismatch")

            date_gap = abs((left["date"] - right["date"]).days)

            if date_gap > max_date_gap_days:
                reasons.append("date_outside_matching_window")

            if not left["reference"] or not right["reference"]:
                reasons.append("reference_missing")
            elif left["reference"] != right["reference"]:
                reasons.append("reference_mismatch")

            if reasons:
                comparisons.append({
                    "transaction_ids": [
                        left["transaction_id"],
                        right["transaction_id"],
                    ],
                    "reasons": reasons,
                })
                continue

            debit_leg = left if left["direction"] == "debit" else right
            credit_leg = right if debit_leg is left else left

            possible_pairs.append({
                "debit": debit_leg,
                "credit": credit_leg,
                "date_gap": date_gap,
            })

    # Count possible matches for each transaction.
    match_counts: dict[Any, int] = {}

    for pair in possible_pairs:
        debit_id = pair["debit"]["transaction_id"]
        credit_id = pair["credit"]["transaction_id"]

        match_counts[debit_id] = match_counts.get(debit_id, 0) + 1
        match_counts[credit_id] = match_counts.get(credit_id, 0) + 1

    candidates: list[dict[str, Any]] = []
    ambiguous_ids: set[Any] = set()
    used_ids: set[Any] = set()

    for pair in possible_pairs:
        debit = pair["debit"]
        credit = pair["credit"]

        debit_id = debit["transaction_id"]
        credit_id = credit["transaction_id"]

        # If either side has more than one possible match, flag ambiguity.
        if (
            match_counts.get(debit_id, 0) > 1
            or match_counts.get(credit_id, 0) > 1
        ):
            ambiguous_ids.add(debit_id)
            ambiguous_ids.add(credit_id)
            continue

        candidates.append({
            "case_type": "internal_transfer",
            "case_status": "suggested",
            "decision": "proposed_only",
            "auto_confirmed": False,
            "confidence_score": None,
            "confidence_label": "high",
            "evidence_strength": "strong",
            "amount": str(debit["amount"]),
            "currency": debit["currency"],
            "reference": debit["reference"],
            "date_gap_days": pair["date_gap"],
            "debit_transaction_id": debit_id,
            "credit_transaction_id": credit_id,
            "source_account_id": debit["account_id"],
            "target_account_id": credit["account_id"],
            "evidence": [
                "same_verified_user",
                "distinct_verified_accounts",
                "opposite_directions",
                "exact_amount_match",
                "currency_match",
                "date_within_window",
                "exact_reference_match",
                "own_account_transfer_narration",
            ],
        })

        used_ids.add(debit_id)
        used_ids.add(credit_id)

    # Ambiguous transactions are visible for manual review.
    for leg in legs:
        tx_id = leg["transaction_id"]

        if tx_id in ambiguous_ids:
            review_required.append(
                _review_item(leg, "multiple_possible_matches")
            )

    # Remaining verified transfer-like transactions are unmatched.
    unmatched: list[dict[str, Any]] = []

    for leg in legs:
        tx_id = leg["transaction_id"]

        if tx_id in used_ids or tx_id in ambiguous_ids:
            continue

        unmatched.append({
            "transaction_id": tx_id,
            "account_id": leg["account_id"],
            "date": leg["date"].isoformat(),
            "direction": leg["direction"],
            "amount": str(leg["amount"]),
            "currency": leg["currency"],
            "reference": leg["reference"],
            "status": "unmatched_candidate",
        })

    return {
        "success": True,
        "mode": "dry_run",
        "writes_performed": False,
        "candidate_count": len(candidates),
        "candidates": candidates,
        "unmatched_count": len(unmatched),
        "unmatched_candidates": unmatched,
        "review_required_count": len(review_required),
        "review_required": review_required,
        "invalid_transaction_ids": invalid_transaction_ids,
        "comparison_diagnostics": comparisons,
        "note": (
            "Candidates are suggestions only. Ambiguous and unverified "
            "transactions require review. No database records were changed."
        ),
    }
