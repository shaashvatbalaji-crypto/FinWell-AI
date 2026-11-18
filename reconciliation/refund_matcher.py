
"""Hackathon prototype: conservative dry-run refund matching."""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Iterable

from reconciliation.reference_extractor import (
    extract_reference,
    references_conflict,
)
from reconciliation.transaction_classifier import classify_transaction


_CENT = Decimal("0.01")

# Words that do not identify an actual merchant.
_GENERIC_WORDS = {
    "PURCHASE", "REFUND", "REVERSAL", "CASHBACK",
    "RETURN", "PAYMENT", "PAID", "DEBIT", "CREDIT",
    "UPI", "POS", "CARD", "ONLINE", "TRANSACTION",
    "TXN", "REF", "REFERENCE", "TO", "FROM",
    "BY", "AT", "FOR",

    # Bank and statement-related words
    "BANK", "STATEMENT", "ACCOUNT", "AC",
    "MERIDIAN", "CREST", "MC",

    # Month names and abbreviations
    "JAN", "JANUARY",
    "FEB", "FEBRUARY",
    "MAR", "MARCH",
    "APR", "APRIL",
    "MAY",
    "JUN", "JUNE",
    "JUL", "JULY",
    "AUG", "AUGUST",
    "SEP", "SEPTEMBER",
    "OCT", "OCTOBER",
    "NOV", "NOVEMBER",
    "DEC", "DECEMBER",

    # Other generic narration words
    "TRANSFER", "SELF", "OWN", "MOBILE",
    "INTERNET", "IMPS", "NEFT", "RTGS",
    "SUCCESSFUL", "COMPLETED",
}


def _money(value: Any) -> Decimal | None:
    """Convert a value into a safe two-decimal monetary amount."""

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
    """Convert supported date values into datetime.date."""

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


def _merchant_key(tx: dict[str, Any]) -> str | None:
    """
    Derive a merchant identity.

    Explicitly supplied merchant metadata takes priority.
    Generic bank narration and statement words are removed.
    """

    supplied = tx.get("normalized_merchant") or tx.get("merchant")

    if supplied:
        value = str(supplied).upper()
    else:
        value = str(tx.get("description") or "").upper()

        # Remove explicitly labelled references.
        value = re.sub(
            r"\b(?:REFERENCE|REF|UTR|RRN|TXN\s*ID|"
            r"TRANSACTION\s*ID|TRANSACTION\s*REF|"
            r"UPI\s*REF|BANK\s*REF)"
            r"\s*[:#=-]?\s*[A-Z0-9/-]+",
            " ",
            value,
        )

    # Extract meaningful alphabetic tokens.
    words = re.findall(r"[A-Z][A-Z&]{1,}", value)

    merchant_words = [
        word for word in words
        if word not in _GENERIC_WORDS
    ]

    if not merchant_words:
        return None

    merchant = " ".join(merchant_words).strip()

    # Reject identities consisting only of short/generic fragments.
    if not any(len(word) >= 3 for word in merchant_words):
        return None

    return merchant or None


def _profile(
    tx: dict[str, Any],
    index: int,
) -> dict[str, Any] | None:
    """Validate and prepare a transaction for refund matching."""

    if not isinstance(tx, dict):
        return None

    debit = _money(tx.get("debit"))
    credit = _money(tx.get("credit"))
    tx_date = _date(tx.get("date") or tx.get("transaction_date"))

    if debit is None or credit is None or tx_date is None:
        return None

    if debit < 0 or credit < 0:
        return None

    if debit > 0 and credit > 0:
        return None

    if debit == 0 and credit == 0:
        return None

    description = tx.get("description")

    if not isinstance(description, str) or not description.strip():
        return None

    classification = classify_transaction(
        description=description,
        debit=debit,
        credit=credit,
        normalized_merchant=tx.get("normalized_merchant"),
    )

    if not classification.get("success"):
        return None

    if debit > 0:
        transaction_type = "purchase"
        amount = debit
    else:
        transaction_type = classification["transaction_type"]
        amount = credit

    return {
        "transaction_id": tx.get(
            "transaction_id",
            f"row_{index + 1}",
        ),
        "user_id": tx.get("user_id"),
        "account_id": tx.get("account_id"),
        "date": tx_date,
        "description": description.strip(),
        "debit": debit,
        "credit": credit,
        "amount": amount,
        "transaction_type": transaction_type,
        "merchant": _merchant_key(tx),
        "reference": extract_reference(description),
        "currency": (
            str(tx["currency"]).strip().upper()
            if tx.get("currency")
            else None
        ),
    }


def _same_scope(
    purchase: dict[str, Any],
    refund: dict[str, Any],
) -> bool:
    """Ensure transactions belong to a compatible user/account scope."""

    if (
        purchase["user_id"] is not None
        and refund["user_id"] is not None
        and purchase["user_id"] != refund["user_id"]
    ):
        return False

    if (
        purchase["account_id"] is not None
        and refund["account_id"] is not None
        and purchase["account_id"] != refund["account_id"]
    ):
        return False

    # Do not assume the same account if only one side has account metadata.
    if (
        (purchase["account_id"] is None)
        != (refund["account_id"] is None)
    ):
        return False

    if (
        purchase["currency"]
        and refund["currency"]
        and purchase["currency"] != refund["currency"]
    ):
        return False

    return True


def _candidate_reason(
    purchase: dict[str, Any],
    refund: dict[str, Any],
    max_date_gap_days: int,
) -> str | None:
    """
    Evaluate whether a purchase and refund could be related.

    A reference conflict rejects the candidate.
    A missing reference produces only a weak candidate.
    """

    if not _same_scope(purchase, refund):
        return None

    # Generic or unidentified merchants cannot establish a match.
    if not purchase["merchant"] or not refund["merchant"]:
        return None

    if purchase["merchant"] != refund["merchant"]:
        return None

    date_gap = (refund["date"] - purchase["date"]).days

    if date_gap < 0 or date_gap > max_date_gap_days:
        return None

    if references_conflict(
        purchase["reference"],
        refund["reference"],
    ):
        return None

    # Strong evidence: both references exist and match.
    if (
        purchase["reference"]
        and refund["reference"]
    ):
        return "reference_match"

    # Weak evidence: merchant and date match, but reference is missing.
    return "merchant_date_match"


def reconcile_refunds(
    transactions: Iterable[dict[str, Any]],
    *,
    max_date_gap_days: int = 90,
) -> dict[str, Any]:
    """
    Match refund credits to original purchase debits.

    Strong reference matches:
        Suggested allocations.

    Missing-reference matches:
        Sent to review_required.

    Multiple partial refunds:
        Supported, subject to the remaining purchase amount.

    This function is in-memory only.
    No database or ChromaDB writes are performed.
    """

    if (
        isinstance(max_date_gap_days, bool)
        or not isinstance(max_date_gap_days, int)
        or max_date_gap_days < 0
    ):
        raise ValueError(
            "max_date_gap_days must be a non-negative integer"
        )

    profiles: list[dict[str, Any]] = []
    invalid_transaction_ids: list[Any] = []

    for index, tx in enumerate(transactions):
        profile = _profile(tx, index)

        if profile is None:
            tx_id = (
                tx.get("transaction_id")
                if isinstance(tx, dict)
                else None
            )
            invalid_transaction_ids.append(tx_id)
            continue

        profiles.append(profile)

    purchases = [
        p for p in profiles
        if p["transaction_type"] == "purchase"
    ]

    refunds = [
        p for p in profiles
        if p["transaction_type"] == "refund"
    ]

    # Track remaining refundable value for every purchase.
    remaining = {
        p["transaction_id"]: p["amount"]
        for p in purchases
    }

    allocations: list[dict[str, Any]] = []
    review_required: list[dict[str, Any]] = []
    unmatched_refunds: list[dict[str, Any]] = []
    over_refunds: list[dict[str, Any]] = []

    for refund in sorted(
        refunds,
        key=lambda item: (
            item["date"],
            str(item["transaction_id"]),
        ),
    ):
        possible: list[tuple[dict[str, Any], str]] = []

        for purchase in purchases:
            reason = _candidate_reason(
                purchase,
                refund,
                max_date_gap_days,
            )

            if reason is not None:
                possible.append((purchase, reason))

        if len(possible) == 0:
            unmatched_refunds.append({
                "refund_transaction_id": refund["transaction_id"],
                "refund_amount": str(refund["amount"]),
                "reason": "no_matching_purchase_found",
                "status": "unmatched",
            })
            continue

        if len(possible) > 1:
            review_required.append({
                "refund_transaction_id": refund["transaction_id"],
                "refund_amount": str(refund["amount"]),
                "possible_purchase_ids": [
                    p["transaction_id"]
                    for p, _ in possible
                ],
                "reason": "multiple_possible_purchases",
                "status": "needs_review",
            })
            continue

        purchase, match_reason = possible[0]
        purchase_id = purchase["transaction_id"]

        # Weak merchant/date-only candidates are never allocated.
        if match_reason != "reference_match":
            review_required.append({
                "refund_transaction_id": refund["transaction_id"],
                "purchase_transaction_id": purchase_id,
                "refund_amount": str(refund["amount"]),
                "purchase_amount": str(purchase["amount"]),
                "merchant": purchase["merchant"],
                "purchase_reference": purchase["reference"],
                "refund_reference": refund["reference"],
                "reason": "reference_missing_weak_match",
                "status": "needs_review",
            })
            continue

        available = remaining[purchase_id]

        if refund["amount"] > available:
            over_refunds.append({
                "purchase_transaction_id": purchase_id,
                "refund_transaction_id": refund["transaction_id"],
                "purchase_amount": str(purchase["amount"]),
                "previously_refunded": str(
                    purchase["amount"] - available
                ),
                "refund_amount": str(refund["amount"]),
                "remaining_before": str(available),
                "reason": "refund_exceeds_remaining_purchase_amount",
                "status": "needs_review",
            })
            continue

        remaining[purchase_id] -= refund["amount"]

        allocations.append({
            "purchase_transaction_id": purchase_id,
            "refund_transaction_id": refund["transaction_id"],
            "purchase_date": purchase["date"].isoformat(),
            "refund_date": refund["date"].isoformat(),
            "merchant": purchase["merchant"],
            "reference": purchase["reference"],
            "purchase_amount": str(purchase["amount"]),
            "refund_amount": str(refund["amount"]),
            "remaining_after": str(remaining[purchase_id]),
            "match_reason": match_reason,
            "confidence_label": "high",
            "status": "suggested",
        })

    purchase_summaries = []

    for purchase in purchases:
        purchase_id = purchase["transaction_id"]
        refunded = purchase["amount"] - remaining[purchase_id]

        purchase_summaries.append({
            "purchase_transaction_id": purchase_id,
            "purchase_amount": str(purchase["amount"]),
            "total_refunded": str(refunded),
            "remaining_expense": str(remaining[purchase_id]),
            "refund_status": (
                "fully_refunded"
                if remaining[purchase_id] == 0
                else "partially_refunded"
                if refunded > 0
                else "not_refunded"
            ),
        })

    total_purchase_amount = sum(
        (p["amount"] for p in purchases),
        Decimal("0.00"),
    )

    total_refunded = sum(
        (
            Decimal(item["refund_amount"])
            for item in allocations
        ),
        Decimal("0.00"),
    )

    total_remaining = sum(
        remaining.values(),
        Decimal("0.00"),
    )

    return {
        "success": True,
        "mode": "dry_run",
        "writes_performed": False,

        "purchase_count": len(purchases),
        "refund_count": len(refunds),

        "allocation_count": len(allocations),
        "allocations": allocations,

        "purchase_summaries": purchase_summaries,

        "total_purchase_amount": str(total_purchase_amount),
        "total_refunded": str(total_refunded),
        "total_remaining_expense": str(total_remaining),

        "review_required_count": len(review_required),
        "review_required": review_required,

        "unmatched_refund_count": len(unmatched_refunds),
        "unmatched_refunds": unmatched_refunds,

        "over_refund_count": len(over_refunds),
        "over_refunds": over_refunds,

        "invalid_transaction_ids": invalid_transaction_ids,

        "note": (
            "Refund matches with matching explicit references are "
            "suggestions only. Missing-reference candidates require "
            "manual review. Original transactions remain unchanged. "
            "No database or ChromaDB writes were made."
        ),
    }
