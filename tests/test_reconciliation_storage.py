
from mysql_pipeline.db import get_db_connection

from mysql_pipeline.reconciliation_storage import (
    save_reconciliation_match,
    list_pending_matches,
    update_match_status
)


def create_test_transactions():
    """Create two temporary transactions for testing."""

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO transactions (
            user_id,
            document_id,
            transaction_date,
            description,
            debit,
            credit,
            balance
        )
        SELECT
            user_id,
            document_id,
            '2026-11-01',
            'TEST DUPLICATE TRANSACTION A',
            500.00,
            0,
            NULL
        FROM documents
        WHERE user_id = 1
        ORDER BY document_id
        LIMIT 1
    """)

    transaction1_id = cursor.lastrowid

    cursor.execute("""
        INSERT INTO transactions (
            user_id,
            document_id,
            transaction_date,
            description,
            debit,
            credit,
            balance
        )
        SELECT
            user_id,
            document_id,
            '2026-11-01',
            'TEST DUPLICATE TRANSACTION B',
            500.00,
            0,
            NULL
        FROM documents
        WHERE user_id = 1
        ORDER BY document_id
        LIMIT 1
    """)

    transaction2_id = cursor.lastrowid

    connection.commit()
    cursor.close()
    connection.close()

    return transaction1_id, transaction2_id


def cleanup_test_data(transaction1_id, transaction2_id, match_id=None):
    """Delete only records created by this test."""

    connection = get_db_connection()
    cursor = connection.cursor()

    if match_id:
        cursor.execute(
            "DELETE FROM reconciliation_matches WHERE match_id = %s",
            (match_id,)
        )

    cursor.execute(
        "DELETE FROM transactions WHERE transaction_id IN (%s, %s)",
        (transaction1_id, transaction2_id)
    )

    connection.commit()
    cursor.close()
    connection.close()


def test_reconciliation_storage():

    transaction1_id = None
    transaction2_id = None
    match_id = None

    try:
        transaction1_id, transaction2_id = create_test_transactions()

        print("Temporary transactions created.")

        # Test saving a match.
        save_result = save_reconciliation_match(
            user_id=1,
            transaction_id=transaction1_id,
            matched_transaction_id=transaction2_id,
            match_type="duplicate",
            confidence_score=0.95,
            match_reason="Controlled test duplicate candidate."
        )

        print("Save result:", save_result)

        assert save_result["success"] is True

        match_id = save_result["match_id"]

        # Test retrieving pending matches.
        pending_result = list_pending_matches(user_id=1)

        print("Pending matches retrieved:", pending_result["success"])

        assert pending_result["success"] is True

        assert any(
            match["match_id"] == match_id
            for match in pending_result["matches"]
        )

        # Test confirming the match.
        review_result = update_match_status(
            user_id=1,
            match_id=match_id,
            new_status="confirmed"
        )

        print("Review result:", review_result)

        assert review_result["success"] is True

        print("\nALL RECONCILIATION STORAGE TESTS PASSED!")

    finally:
        if transaction1_id and transaction2_id:
            cleanup_test_data(
                transaction1_id,
                transaction2_id,
                match_id
            )
            print("Temporary test data cleaned up.")


if __name__ == "__main__":
    test_reconciliation_storage()
