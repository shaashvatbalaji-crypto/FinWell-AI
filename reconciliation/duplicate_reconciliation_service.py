
from itertools import combinations

from mysql.connector import Error

from mysql_pipeline.db import get_db_connection
from mysql_pipeline.reconciliation_storage import (
    save_reconciliation_match
)
from reconciliation.duplicate_detector import (
    detect_duplicate_candidate
)


def fetch_user_transactions(user_id):
    """Fetch transactions belonging to one user."""

    connection = None
    cursor = None

    try:
        connection = get_db_connection()

        if connection is None:
            raise RuntimeError("Could not connect to MySQL.")

        cursor = connection.cursor(dictionary=True)

        query = """
            SELECT
                transaction_id,
                user_id,
                document_id,
                transaction_date,
                description,
                debit,
                credit
            FROM transactions
            WHERE user_id = %s
            ORDER BY transaction_date, transaction_id
        """

        cursor.execute(query, (user_id,))
        return cursor.fetchall()

    except Error as error:
        raise RuntimeError(
            f"Could not fetch transactions: {error}"
        ) from error

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()


def run_duplicate_reconciliation(
    user_id,
    dry_run=True
):
    """
    Analyse all transaction pairs belonging to a user.

    dry_run=True:
        Detect candidates without saving anything.

    dry_run=False:
        Save candidates as suggested matches in MySQL.

    Existing confirmed or rejected matches are not overwritten.
    """

    if not user_id:
        return {
            "success": False,
            "message": "A valid user_id is required."
        }

    try:
        transactions = fetch_user_transactions(user_id)

        if len(transactions) < 2:
            return {
                "success": True,
                "user_id": user_id,
                "total_transactions": len(transactions),
                "total_pairs_checked": 0,
                "candidate_count": 0,
                "saved_count": 0,
                "dry_run": dry_run,
                "candidates": [],
                "message": "Not enough transactions to compare."
            }

        candidates = []
        saved_count = 0
        storage_errors = []

        total_pairs_checked = 0

        for transaction1, transaction2 in combinations(
            transactions, 2
        ):

            total_pairs_checked += 1

            result = detect_duplicate_candidate(
                transaction1,
                transaction2
            )

            if not result.get("is_candidate"):
                continue

            candidate = {
                **result,
                "storage_status": (
                    "dry_run" if dry_run else "not_saved"
                )
            }

            if not dry_run:

                save_result = save_reconciliation_match(
                    user_id=user_id,
                    transaction_id=result["transaction_id"],
                    matched_transaction_id=result[
                        "matched_transaction_id"
                    ],
                    match_type="duplicate",
                    confidence_score=result["confidence_score"],
                    match_reason=result["match_reason"]
                )

                if save_result["success"]:
                    candidate["storage_status"] = "saved_or_existing"
                    candidate["match_id"] = save_result.get("match_id")
                    saved_count += 1
                else:
                    candidate["storage_status"] = "failed"
                    candidate["storage_error"] = save_result["message"]

                    storage_errors.append({
                        "transaction_id": result["transaction_id"],
                        "matched_transaction_id": result[
                            "matched_transaction_id"
                        ],
                        "error": save_result["message"]
                    })

            candidates.append(candidate)

        return {
            "success": len(storage_errors) == 0,
            "user_id": user_id,
            "total_transactions": len(transactions),
            "total_pairs_checked": total_pairs_checked,
            "candidate_count": len(candidates),
            "saved_count": saved_count,
            "storage_error_count": len(storage_errors),
            "dry_run": dry_run,
            "candidates": candidates,
            "storage_errors": storage_errors,
            "message": (
                "Duplicate analysis completed successfully."
                if not storage_errors
                else "Analysis completed with storage errors."
            )
        }

    except (RuntimeError, Error) as error:
        return {
            "success": False,
            "message": str(error)
        }
