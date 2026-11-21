
from mysql.connector import Error
from mysql_pipeline.db import get_db_connection


def save_reconciliation_match(
    user_id,
    transaction_id,
    matched_transaction_id,
    match_type,
    confidence_score,
    match_reason
):
    """
    Save a suggested reconciliation match.

    Both transactions must belong to the same user.
    Matches are always initially saved as suggested.
    """

    allowed_types = {
        "duplicate",
        "internal_transfer",
        "refund"
    }

    if match_type not in allowed_types:
        return {
            "success": False,
            "message": "Invalid match type."
        }

    if transaction_id == matched_transaction_id:
        return {
            "success": False,
            "message": "A transaction cannot match itself."
        }

    try:
        score = float(confidence_score)
    except (TypeError, ValueError):
        return {
            "success": False,
            "message": "Invalid confidence score."
        }

    if not 0 <= score <= 1:
        return {
            "success": False,
            "message": "Confidence score must be between 0 and 1."
        }

    # Canonical ordering prevents mirrored A-B and B-A records.
    first_id = min(transaction_id, matched_transaction_id)
    second_id = max(transaction_id, matched_transaction_id)

    connection = None
    cursor = None

    try:
        connection = get_db_connection()

        if connection is None:
            return {
                "success": False,
                "message": "Could not connect to MySQL."
            }

        cursor = connection.cursor(dictionary=True)

        # Verify both transactions exist and belong to this user.
        cursor.execute(
            """
            SELECT transaction_id
            FROM transactions
            WHERE user_id = %s
              AND transaction_id IN (%s, %s)
            """,
            (user_id, first_id, second_id)
        )

        owned_transactions = cursor.fetchall()

        if len(owned_transactions) != 2:
            return {
                "success": False,
                "message": (
                    "Both transactions must exist and belong "
                    "to the specified user."
                )
            }

        # Avoid saving an already existing match.
        cursor.execute(
            """
            SELECT match_id
            FROM reconciliation_matches
            WHERE transaction_id = %s
              AND matched_transaction_id = %s
              AND match_type = %s
            LIMIT 1
            """,
            (first_id, second_id, match_type)
        )

        existing_match = cursor.fetchone()

        if existing_match:
            return {
                "success": True,
                "match_id": existing_match["match_id"],
                "message": "This reconciliation match already exists."
            }

        cursor.execute(
            """
            INSERT INTO reconciliation_matches (
                transaction_id,
                matched_transaction_id,
                match_type,
                confidence_score,
                match_status,
                match_reason
            )
            VALUES (%s, %s, %s, %s, 'suggested', %s)
            """,
            (
                first_id,
                second_id,
                match_type,
                score,
                match_reason
            )
        )

        match_id = cursor.lastrowid
        connection.commit()

        return {
            "success": True,
            "match_id": match_id,
            "message": "Reconciliation match saved successfully."
        }

    except Error as error:
        if connection:
            connection.rollback()

        return {
            "success": False,
            "message": f"MySQL error: {error}"
        }

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()


def list_pending_matches(user_id, limit=100):
    """Retrieve suggested matches belonging to a user."""

    connection = None
    cursor = None

    try:
        connection = get_db_connection()

        if connection is None:
            return {
                "success": False,
                "matches": [],
                "message": "Could not connect to MySQL."
            }

        cursor = connection.cursor(dictionary=True)

        query = """
            SELECT
                rm.match_id,
                rm.transaction_id,
                rm.matched_transaction_id,
                rm.match_type,
                rm.confidence_score,
                rm.match_status,
                rm.match_reason,
                rm.created_at,
                t1.transaction_date AS first_date,
                t1.description AS first_description,
                t1.debit AS first_debit,
                t1.credit AS first_credit,
                t1.account_id AS first_account_id,
                a1.account_name AS first_account_name,
                a1.currency AS first_currency,
                t2.transaction_date AS second_date,
                t2.description AS second_description,
                t2.debit AS second_debit,
                t2.credit AS second_credit,
                t2.account_id AS second_account_id,
                a2.account_name AS second_account_name,
                a2.currency AS second_currency
            FROM reconciliation_matches rm
            INNER JOIN transactions t1
                ON rm.transaction_id = t1.transaction_id
            LEFT JOIN accounts a1
                ON t1.account_id = a1.account_id
               AND a1.user_id = %s
            INNER JOIN transactions t2
                ON rm.matched_transaction_id = t2.transaction_id
            LEFT JOIN accounts a2
                ON t2.account_id = a2.account_id
               AND a2.user_id = %s
            WHERE t1.user_id = %s
              AND t2.user_id = %s
              AND rm.match_status = 'suggested'
            ORDER BY rm.confidence_score DESC, rm.created_at DESC
            LIMIT %s
        """

        cursor.execute(query, (user_id, user_id, user_id, user_id, limit))

        matches = cursor.fetchall()

        return {
            "success": True,
            "matches": matches,
            "message": "Pending reconciliation matches retrieved."
        }

    except Error as error:
        return {
            "success": False,
            "matches": [],
            "message": f"MySQL error: {error}"
        }

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()


def update_match_status(user_id, match_id, new_status):
    """
    Confirm or reject a suggested match.

    Only suggested matches can be reviewed.
    """

    if new_status not in {"confirmed", "rejected"}:
        return {
            "success": False,
            "message": "Status must be confirmed or rejected."
        }

    connection = None
    cursor = None

    try:
        connection = get_db_connection()

        if connection is None:
            return {
                "success": False,
                "message": "Could not connect to MySQL."
            }

        cursor = connection.cursor()

        query = """
            UPDATE reconciliation_matches rm
            INNER JOIN transactions t1
                ON rm.transaction_id = t1.transaction_id
            INNER JOIN transactions t2
                ON rm.matched_transaction_id = t2.transaction_id
            SET rm.match_status = %s
            WHERE rm.match_id = %s
              AND t1.user_id = %s
              AND t2.user_id = %s
              AND rm.match_status = 'suggested'
        """

        cursor.execute(
            query,
            (new_status, match_id, user_id, user_id)
        )

        if cursor.rowcount == 0:
            connection.rollback()

            return {
                "success": False,
                "message": (
                    "Match not found, not owned by this user, "
                    "or already reviewed."
                )
            }

        connection.commit()

        return {
            "success": True,
            "match_id": match_id,
            "new_status": new_status,
            "message": f"Match successfully marked as {new_status}."
        }

    except Error as error:
        if connection:
            connection.rollback()

        return {
            "success": False,
            "message": f"MySQL error: {error}"
        }

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()
