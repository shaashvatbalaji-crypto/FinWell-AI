
"""
FinWell AI - Ingestion Shadow Reconciliation Service

Purpose:
    Analyse incoming normalized transactions for possible duplicates
    before the normal ingestion process stores them.

Safety:
    - Read-only access to existing MySQL transactions.
    - No reconciliation case creation.
    - No reconciliation match storage.
    - No transaction insert, update or delete.
    - No ChromaDB operations.
    - No automatic duplicate confirmation.

The existing production duplicate detector is reused.
All candidate results are suggestions only.
"""

import logging
from itertools import combinations

from mysql_pipeline.db import get_db_connection
from reconciliation.duplicate_detector import (
    detect_duplicate_candidate,
)

logger = logging.getLogger(__name__)


def _build_incoming_transaction(
    transaction,
    index,
    user_id,
    document_id,
    account_id,
):
    """
    Convert a normalized transaction into the structure
    expected by the existing duplicate detector.

    Negative transaction IDs are temporary in-memory identifiers.
    They are never written to MySQL.
    """

    return {
        "transaction_id": -(index + 1),
        "user_id": user_id,
        "document_id": document_id,
        "account_id": account_id,
        "transaction_date": transaction.get("date"),
        "description": transaction.get("description", ""),
        "debit": transaction.get("debit"),
        "credit": transaction.get("credit"),
    }


def _fetch_account_transactions(user_id, account_id):
    """
    Fetch existing transactions belonging to the same user
    and the same known account.

    This function performs SELECT only.
    """

    connection = None
    cursor = None

    try:
        connection = get_db_connection()

        if connection is None:
            raise RuntimeError(
                "Could not establish MySQL connection."
            )

        cursor = connection.cursor(dictionary=True)

        query = """
            SELECT
                transaction_id,
                user_id,
                document_id,
                account_id,
                transaction_date,
                description,
                debit,
                credit
            FROM transactions
            WHERE user_id = %s
              AND account_id = %s
            ORDER BY transaction_date, transaction_id
        """

        cursor.execute(
            query,
            (user_id, account_id),
        )

        return cursor.fetchall()

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None:
            connection.close()


def _analyse_existing_transactions(
    incoming_transactions,
    existing_transactions,
):
    """
    Compare incoming transactions against previously stored
    transactions from the same account.
    """

    candidates = []
    pairs_checked = 0

    for incoming_index, incoming in enumerate(
        incoming_transactions
    ):

        for existing in existing_transactions:

            pairs_checked += 1

            candidate = detect_duplicate_candidate(
                incoming,
                existing,
            )

            if not candidate.get("is_candidate"):
                continue

            candidates.append({
                **candidate,
                "incoming_transaction_index": incoming_index,
                "existing_transaction_id": (
                    existing["transaction_id"]
                ),
                "candidate_scope": "incoming_vs_existing",
                "storage_status": "not_saved_shadow_mode",
                "decision_status": "requires_review",
            })

    return candidates, pairs_checked


def _analyse_incoming_transactions(incoming_transactions):
    """
    Compare transactions within the same incoming document.
    """

    candidates = []
    pairs_checked = 0

    for index1, index2 in combinations(
        range(len(incoming_transactions)),
        2,
    ):

        transaction1 = incoming_transactions[index1]
        transaction2 = incoming_transactions[index2]

        pairs_checked += 1

        candidate = detect_duplicate_candidate(
            transaction1,
            transaction2,
        )

        if not candidate.get("is_candidate"):
            continue

        candidates.append({
            **candidate,
            "incoming_transaction_index": index1,
            "matched_incoming_transaction_index": index2,
            "candidate_scope": "within_incoming_document",
            "storage_status": "not_saved_shadow_mode",
            "decision_status": "requires_review",
        })

    return candidates, pairs_checked


def analyze_incoming_transactions(
    user_id,
    document_id,
    account_id,
    transactions,
):
    """
    Run read-only duplicate candidate analysis.

    This function is designed to be called after transaction
    validation and before the existing transaction storage step.

    It does not interrupt normal ingestion if shadow analysis fails.
    """

    result = {
        "success": True,
        "mode": "shadow",
        "read_only": True,
        "user_id": user_id,
        "document_id": document_id,
        "account_id": account_id,
        "incoming_transaction_count": len(
            transactions or []
        ),
        "existing_transaction_count": 0,
        "pairs_checked": 0,
        "duplicate_candidate_count": 0,
        "candidates": [],
        "skipped": False,
        "message": None,
        "other_reconciliation_types": {
            "internal_transfers": "not_implemented",
            "refunds": "not_implemented",
            "settlements": "not_implemented",
        },
    }

    if not user_id or not document_id:
        result["success"] = False
        result["message"] = (
            "A valid user_id and document_id are required."
        )
        return result

    if not transactions:
        result["message"] = (
            "No valid transactions available for reconciliation."
        )
        return result

    # Never compare transactions when the account association
    # is unknown. This prevents cross-account false positives.
    if account_id is None:
        result["skipped"] = True
        result["message"] = (
            "Duplicate analysis skipped because account_id "
            "is not linked to this document."
        )
        return result

    try:
        incoming_transactions = [
            _build_incoming_transaction(
                transaction=transaction,
                index=index,
                user_id=user_id,
                document_id=document_id,
                account_id=account_id,
            )
            for index, transaction in enumerate(transactions)
        ]

        existing_transactions = _fetch_account_transactions(
            user_id=user_id,
            account_id=account_id,
        )

        result["existing_transaction_count"] = len(
            existing_transactions
        )

        # Compare against existing stored transactions.
        existing_candidates, existing_pairs = (
            _analyse_existing_transactions(
                incoming_transactions,
                existing_transactions,
            )
        )

        # Compare transactions within the incoming PDF.
        incoming_candidates, incoming_pairs = (
            _analyse_incoming_transactions(
                incoming_transactions
            )
        )

        all_candidates = (
            existing_candidates + incoming_candidates
        )

        result["pairs_checked"] = (
            existing_pairs + incoming_pairs
        )

        result["candidates"] = all_candidates

        result["duplicate_candidate_count"] = len(
            all_candidates
        )

        result["message"] = (
            "Shadow duplicate analysis completed. "
            "All candidates require review."
        )

        return result

    except Exception as error:

        logger.exception(
            "Shadow reconciliation failed for document_id=%s",
            document_id,
        )

        # Do not fail normal document ingestion because
        # the optional shadow analysis encountered an error.
        result["success"] = False
        result["message"] = (
            "Shadow reconciliation failed: "
            + str(error)
        )

        return result
