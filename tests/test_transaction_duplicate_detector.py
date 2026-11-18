
from reconciliation.duplicate_detector import detect_duplicate_candidate


def make_transaction(
    transaction_id,
    document_id,
    description,
    transaction_date,
    debit=0,
    credit=0,
    user_id=1
):
    return {
        "transaction_id": transaction_id,
        "user_id": user_id,
        "document_id": document_id,
        "transaction_date": transaction_date,
        "description": description,
        "debit": debit,
        "credit": credit
    }


def test_duplicate_detection():

    transaction1 = make_transaction(
        101, 10,
        "POS PURCHASE FRESHBASKET MART CHENNAI",
        "2026-10-03",
        debit="2846.50"
    )

    transaction2 = make_transaction(
        201, 11,
        "POS PURCHASE FRESHBASKET MART CHENNAI",
        "2026-10-03",
        debit="2846.50"
    )

    result = detect_duplicate_candidate(
        transaction1, transaction2
    )

    print("\nExact cross-document match:", result)

    assert result["is_candidate"] is True
    assert result["confidence_score"] >= 0.90

    # Different amounts should not match.
    transaction3 = make_transaction(
        202, 11,
        "POS PURCHASE FRESHBASKET MART CHENNAI",
        "2026-10-03",
        debit="1732.25"
    )

    result = detect_duplicate_candidate(
        transaction1, transaction3
    )

    assert result["is_candidate"] is False

    # Different users must never be compared as duplicates.
    transaction4 = make_transaction(
        203, 12,
        "POS PURCHASE FRESHBASKET MART CHENNAI",
        "2026-10-03",
        debit="2846.50",
        user_id=2
    )

    result = detect_duplicate_candidate(
        transaction1, transaction4
    )

    assert result["is_candidate"] is False

    # Different debit/credit directions must not match.
    transaction5 = make_transaction(
        204, 11,
        "POS PURCHASE FRESHBASKET MART CHENNAI",
        "2026-10-03",
        credit="2846.50"
    )

    result = detect_duplicate_candidate(
        transaction1, transaction5
    )

    assert result["is_candidate"] is False

    print("\nAll duplicate detection tests passed!")


if __name__ == "__main__":
    test_duplicate_detection()
