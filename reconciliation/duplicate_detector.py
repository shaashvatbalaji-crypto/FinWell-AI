
import re

from datetime import date
from difflib import SequenceMatcher

from reconciliation.transaction_features import (
    extract_transaction_features,
)

from reconciliation.reference_extractor import (
    references_conflict,
)


# Prototype configuration.
# These values can later move into a configuration file or database.

MAX_DATE_DIFFERENCE_DAYS = 2

MIN_DESCRIPTION_SIMILARITY = 0.50
MIN_SAME_DOCUMENT_SIMILARITY = 0.90

SCORE_BASE = 0.35
SCORE_SAME_DATE = 0.30
SCORE_ONE_DAY = 0.20
SCORE_TWO_DAYS = 0.10
SCORE_DESCRIPTION_WEIGHT = 0.35

GENERIC_WORDS = {
    "POS", "PURCHASE", "UPI", "DR", "CR",
    "PAYMENT", "TRANSACTION", "CHENNAI",
    "ORDER", "ONLINE", "PAY", "DEBIT",
    "CREDIT", "MART", "FOODS", "RESTAURANT",
    "REF", "REFERENCE", "UTR", "RRN",
    "TXN", "ID", "TRANSACTION"
}

IMPORTANT_DETAILS = {
    "LUNCH", "DINNER", "BREAKFAST",
    "MORNING", "EVENING", "NIGHT",
    "RENT", "EMI", "RECHARGE",
    "REFUND", "CASHBACK"
}


def extract_important_details(description):
    tokens = set(
        re.findall(r"[A-Z]+", str(description).upper())
    )

    return tokens.intersection(IMPORTANT_DETAILS)


def calculate_description_similarity(
    description1,
    description2,
    merchant1=None,
    merchant2=None,
):
    """
    Calculate similarity using merchant identity and
    normalized description tokens.
    """

    if merchant1 and merchant2:
        if merchant1 != merchant2:
            return 0.0

        return 1.0

    tokens1 = set(
        re.findall(r"[A-Z0-9]+", str(description1).upper())
    )

    tokens2 = set(
        re.findall(r"[A-Z0-9]+", str(description2).upper())
    )

    tokens1 -= GENERIC_WORDS
    tokens2 -= GENERIC_WORDS

    if not tokens1 or not tokens2:
        return 0.0

    intersection = len(tokens1.intersection(tokens2))
    union = len(tokens1.union(tokens2))

    jaccard_similarity = intersection / union

    sequence_similarity = SequenceMatcher(
        None,
        " ".join(sorted(tokens1)),
        " ".join(sorted(tokens2)),
    ).ratio()

    return round(
        (0.70 * jaccard_similarity)
        + (0.30 * sequence_similarity),
        4,
    )


def rejected(reason):
    return {
        "is_candidate": False,
        "reason": reason,
    }


def compare_features(feature1, feature2):
    """Compare two standardized transaction feature dictionaries."""

    if (
        feature1["transaction_id"] is not None
        and feature1["transaction_id"]
        == feature2["transaction_id"]
    ):
        return rejected(
            "Cannot compare a transaction with itself."
        )

    if (
        feature1["user_id"] is not None
        and feature2["user_id"] is not None
        and feature1["user_id"] != feature2["user_id"]
    ):
        return rejected(
            "Transactions belong to different users."
        )

    account1 = feature1["account_id"]
    account2 = feature2["account_id"]

    if (
        account1 is not None
        and account2 is not None
        and account1 != account2
    ):
        return rejected(
            "Transactions belong to different accounts."
        )

    currency1 = feature1["currency"]
    currency2 = feature2["currency"]

    if (
        currency1 is not None
        and currency2 is not None
        and currency1 != currency2
    ):
        return rejected(
            "Transaction currencies do not match."
        )

    if references_conflict(
        feature1["reference"],
        feature2["reference"],
    ):
        return rejected(
            "Transaction references do not match."
        )

    amount1 = feature1["amount"]
    amount2 = feature2["amount"]

    if amount1 == 0 or amount2 == 0:
        return rejected(
            "Transaction amount is zero or missing."
        )

    if amount1 != amount2:
        return rejected(
            "Transaction amounts do not match."
        )

    direction1 = feature1["direction"]
    direction2 = feature2["direction"]

    if direction1 != direction2:
        return rejected(
            "Debit and credit directions do not match."
        )

    date_difference = abs(
        (
            feature1["transaction_date"]
            - feature2["transaction_date"]
        ).days
    )

    if date_difference > MAX_DATE_DIFFERENCE_DAYS:
        return rejected(
            "Transaction dates are too far apart."
        )

    details1 = extract_important_details(
        feature1["description"]
    )

    details2 = extract_important_details(
        feature2["description"]
    )

    if details1 and details2 and details1.isdisjoint(details2):
        return rejected(
            "Transaction details conflict."
        )

    merchant1 = feature1["merchant"]
    merchant2 = feature2["merchant"]

    if (
        merchant1 is not None
        and merchant2 is not None
        and merchant1 != merchant2
    ):
        return rejected(
            "Merchant names do not match."
        )

    similarity = calculate_description_similarity(
        feature1["description"],
        feature2["description"],
        merchant1,
        merchant2,
    )

    same_document = (
        feature1["document_id"] is not None
        and feature2["document_id"] is not None
        and feature1["document_id"]
        == feature2["document_id"]
    )

    if similarity < MIN_DESCRIPTION_SIMILARITY:
        return rejected(
            "Transaction descriptions are not sufficiently similar."
        )

    if (
        same_document
        and similarity < MIN_SAME_DOCUMENT_SIMILARITY
    ):
        return rejected(
            "Same-document descriptions lack strong similarity."
        )

    score = SCORE_BASE

    if date_difference == 0:
        score += SCORE_SAME_DATE
    elif date_difference == 1:
        score += SCORE_ONE_DAY
    else:
        score += SCORE_TWO_DAYS

    score += SCORE_DESCRIPTION_WEIGHT * similarity

    score = round(min(score, 1.0), 4)

    return {
        "is_candidate": True,
        "transaction_id": feature1["transaction_id"],
        "matched_transaction_id": feature2["transaction_id"],
        "match_type": "duplicate",
        "confidence_score": score,
        "date_difference_days": date_difference,
        "description_similarity": round(similarity, 4),
        "same_document": same_document,
        "match_evidence": {
            "amount_match": True,
            "direction_match": True,
            "account_match": (
                account1 == account2
                if account1 is not None and account2 is not None
                else None
            ),
            "currency_match": (
                currency1 == currency2
                if currency1 is not None and currency2 is not None
                else None
            ),
            "reference_match": (
                feature1["reference"] == feature2["reference"]
                if (
                    feature1["reference"] is not None
                    and feature2["reference"] is not None
                )
                else None
            ),
            "merchant_match": (
                merchant1 == merchant2
                if merchant1 is not None and merchant2 is not None
                else None
            ),
        },
        "match_reason": (
            "Matching amount and direction, compatible account "
            "and currency information, compatible references, "
            "and similar merchant, description and date."
        ),
    }


def detect_duplicate_candidate(
    transaction1,
    transaction2,
    merchant_aliases=None,
    reference_labels=None,
):
    """
    Public interface retained for compatibility.

    Returns a duplicate candidate result without modifying
    either original transaction.
    """

    try:
        feature1 = extract_transaction_features(
            transaction1,
            merchant_aliases=merchant_aliases,
            reference_labels=reference_labels,
        )

        feature2 = extract_transaction_features(
            transaction2,
            merchant_aliases=merchant_aliases,
            reference_labels=reference_labels,
        )

        return compare_features(feature1, feature2)

    except (ValueError, TypeError, KeyError) as error:
        return rejected(
            f"Unable to compare transactions: {error}"
        )
