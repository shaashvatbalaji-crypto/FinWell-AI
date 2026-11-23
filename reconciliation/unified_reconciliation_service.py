
"""
Unified Reconciliation Coordinator - FinWell AI

Coordinates existing reconciliation engines in memory.

Supported:
- Duplicate detection
- Internal transfer matching
- Refund matching
- Gateway settlement matching
- Statement balance reconciliation

Safety:
- No MySQL writes
- No ChromaDB writes
- No transaction deletion or modification
- No automatic confirmation of matches
- Each engine's result is preserved independently
"""

from copy import deepcopy
from itertools import combinations
from typing import Any

from reconciliation.duplicate_detector import detect_duplicate_candidate
from reconciliation.internal_transfer_matcher import (
    reconcile_internal_transfers,
)
from reconciliation.refund_matcher import reconcile_refunds
from reconciliation.settlement_matcher import reconcile_settlements
from reconciliation.balance_reconciler import (
    reconcile_statement_balance,
)


def _prepare_transactions(transactions):
    """Create independent transaction copies with date aliases."""
    prepared = []

    for transaction in transactions:
        if not isinstance(transaction, dict):
            prepared.append(transaction)
            continue

        item = deepcopy(transaction)

        if item.get("date") is None:
            item["date"] = item.get("transaction_date")

        if item.get("transaction_date") is None:
            item["transaction_date"] = item.get("date")

        prepared.append(item)

    return prepared


def _is_duplicate_candidate(result):
    """Interpret common candidate indicators without changing engine output."""
    if not isinstance(result, dict):
        return False

    for key in (
        "is_duplicate",
        "is_duplicate_candidate",
        "duplicate_candidate",
        "is_candidate",
    ):
        if result.get(key) is True:
            return True

    return False


def _run_engine(engine_name, callback):
    """Run one engine without allowing its failure to stop other engines."""
    try:
        result = callback()

        if not isinstance(result, dict):
            return {
                "success": False,
                "message": "Engine returned an unexpected result.",
                "raw_result": result,
            }

        return result

    except Exception as error:
        return {
            "success": False,
            "message": f"{engine_name} failed.",
            "error": str(error),
        }


def _collect_exceptions(engine_results):
    """Collect review, unmatched and invalid items from engine outputs."""
    exceptions = []

    collection_fields = (
        "review_required",
        "unmatched_candidates",
        "unmatched_refunds",
        "unmatched_transactions",
        "invalid_transactions",
        "invalid_transaction_ids",
        "over_refunds",
        "running_balance_mismatches",
    )

    for engine_name, result in engine_results.items():
        if not isinstance(result, dict):
            continue

        for field in collection_fields:
            items = result.get(field)

            if not isinstance(items, list):
                continue

            for item in items:
                exceptions.append({
                    "engine": engine_name,
                    "exception_type": field,
                    "details": item,
                })

        if result.get("success") is False:
            exceptions.append({
                "engine": engine_name,
                "exception_type": "engine_error",
                "details": result.get("message", "Engine failed."),
            })

    return exceptions


def reconcile_all_transactions(
    transactions,
    *,
    existing_transactions=None,
    accounts=None,
    gateway_transactions=None,
    bank_transactions=None,
    opening_balance=None,
    closing_balance=None,
    balance_tolerance="0.01",
    check_running_balance=True,
    max_transfer_date_gap_days=1,
    max_refund_date_gap_days=90,
    max_settlement_date_gap_days=5,
):
    """
    Run the available reconciliation engines in one dry-run operation.

    Required:
        transactions:
            Transactions from the statement being analysed.

    Optional:
        existing_transactions:
            Previously stored transactions supplied by the caller.
            Used only for duplicate comparisons.

        accounts:
            Verified account metadata required by the transfer matcher.

        gateway_transactions / bank_transactions:
            Explicitly separated transaction lists for settlement matching.

        opening_balance / closing_balance:
            Both required to run statement balance reconciliation.

    Returns:
        Structured engine results, exceptions and summary.

    This function performs no database or ChromaDB writes.
    """

    output = {
        "success": True,
        "mode": "dry_run",
        "writes_performed": False,
        "original_transactions_modified": False,
        "engines": {},
        "exceptions": [],
        "summary": {},
        "message": None,
    }

    # ---------------------------------------------------------
    # 1. Validate incoming transactions
    # ---------------------------------------------------------

    if not isinstance(transactions, list):
        output["success"] = False
        output["message"] = "transactions must be provided as a list."
        return output

    if not transactions:
        output["success"] = False
        output["message"] = "No incoming transactions were provided."
        return output

    invalid_input_indexes = [
        index
        for index, transaction in enumerate(transactions)
        if not isinstance(transaction, dict)
    ]

    if invalid_input_indexes:
        output["success"] = False
        output["message"] = (
            "Incoming transactions must all be dictionaries."
        )
        output["invalid_input_indexes"] = invalid_input_indexes
        return output

    if existing_transactions is None:
        existing_transactions = []

    if not isinstance(existing_transactions, list):
        output["success"] = False
        output["message"] = (
            "existing_transactions must be a list when provided."
        )
        return output

    if accounts is None:
        accounts = {}

    if not isinstance(accounts, (dict, list)):
        output["success"] = False
        output["message"] = "accounts must be a dictionary or list."
        return output

    incoming = _prepare_transactions(transactions)
    existing = _prepare_transactions(existing_transactions)

    # ---------------------------------------------------------
    # 2. Duplicate detection
    # ---------------------------------------------------------

    duplicate_comparisons = []
    duplicate_candidates = []

    comparison_pairs = []

    # Compare incoming transactions against supplied existing records.
    for incoming_tx in incoming:
        for existing_tx in existing:
            comparison_pairs.append((incoming_tx, existing_tx, "existing"))

    # Also check for duplicates within the incoming statement.
    for first_tx, second_tx in combinations(incoming, 2):
        comparison_pairs.append((first_tx, second_tx, "incoming_batch"))

    for first_tx, second_tx, comparison_scope in comparison_pairs:
        result = _run_engine(
            "duplicate_detection",
            lambda a=first_tx, b=second_tx: detect_duplicate_candidate(
                a,
                b,
            ),
        )

        comparison = {
            "comparison_scope": comparison_scope,
            "transaction1_id": first_tx.get("transaction_id"),
            "transaction2_id": second_tx.get("transaction_id"),
            "result": result,
        }

        duplicate_comparisons.append(comparison)

        if _is_duplicate_candidate(result):
            duplicate_candidates.append(comparison)

    output["engines"]["duplicates"] = {
        "success": True,
        "comparison_count": len(duplicate_comparisons),
        "candidate_count": len(duplicate_candidates),
        "comparisons": duplicate_comparisons,
        "candidates": duplicate_candidates,
        "message": (
            "Duplicate comparisons completed."
            if duplicate_comparisons
            else "No comparison pairs were available."
        ),
    }

    # ---------------------------------------------------------
    # 3. Internal transfer matching
    # ---------------------------------------------------------

    if accounts:
        output["engines"]["internal_transfers"] = _run_engine(
            "internal_transfer_matching",
            lambda: reconcile_internal_transfers(
                incoming,
                accounts,
                max_date_gap_days=max_transfer_date_gap_days,
            ),
        )
    else:
        output["engines"]["internal_transfers"] = {
            "success": True,
            "status": "skipped",
            "message": (
                "Account metadata was not supplied. "
                "Transfer matching requires verified account ownership."
            ),
        }

    # ---------------------------------------------------------
    # 4. Refund matching
    # ---------------------------------------------------------

    output["engines"]["refunds"] = _run_engine(
        "refund_matching",
        lambda: reconcile_refunds(
            incoming,
            max_date_gap_days=max_refund_date_gap_days,
        ),
    )

    # ---------------------------------------------------------
    # 5. Settlement matching
    # ---------------------------------------------------------

    if (
        gateway_transactions is not None
        and bank_transactions is not None
    ):
        if (
            not isinstance(gateway_transactions, list)
            or not isinstance(bank_transactions, list)
        ):
            output["engines"]["settlements"] = {
                "success": False,
                "message": (
                    "Gateway and bank transactions must both be lists."
                ),
            }
        else:
            gateway_input = _prepare_transactions(
                gateway_transactions
            )
            bank_input = _prepare_transactions(bank_transactions)

            output["engines"]["settlements"] = _run_engine(
                "settlement_matching",
                lambda: reconcile_settlements(
                    gateway_input,
                    bank_input,
                    max_date_gap_days=max_settlement_date_gap_days,
                ),
            )
    else:
        output["engines"]["settlements"] = {
            "success": True,
            "status": "skipped",
            "message": (
                "Separate gateway and bank transaction lists "
                "were not both supplied."
            ),
        }

    # ---------------------------------------------------------
    # 6. Statement balance reconciliation
    # ---------------------------------------------------------

    if opening_balance is not None and closing_balance is not None:
        output["engines"]["balance"] = _run_engine(
            "balance_reconciliation",
            lambda: reconcile_statement_balance(
                incoming,
                opening_balance,
                closing_balance,
                tolerance=balance_tolerance,
                check_running_balance=check_running_balance,
            ),
        )
    else:
        output["engines"]["balance"] = {
            "success": True,
            "status": "skipped",
            "message": (
                "Opening and closing balances were not both supplied."
            ),
        }

    # ---------------------------------------------------------
    # 7. Collect exceptions
    # ---------------------------------------------------------

    output["exceptions"] = _collect_exceptions(
        output["engines"]
    )

    # ---------------------------------------------------------
    # 8. Summary
    # ---------------------------------------------------------

    transfer_result = output["engines"]["internal_transfers"]
    refund_result = output["engines"]["refunds"]
    settlement_result = output["engines"]["settlements"]
    balance_result = output["engines"]["balance"]

    output["summary"] = {
        "incoming_transaction_count": len(incoming),
        "existing_transaction_count": len(existing),
        "duplicate_comparison_count": len(duplicate_comparisons),
        "duplicate_candidate_count": len(duplicate_candidates),
        "transfer_candidate_count": len(
            transfer_result.get("candidates", [])
        ) if isinstance(transfer_result, dict) else 0,
        "refund_allocation_count": refund_result.get(
            "allocation_count", 0
        ) if isinstance(refund_result, dict) else 0,
        "settlement_candidate_count": settlement_result.get(
            "candidate_count",
            len(settlement_result.get("matches", []))
            if isinstance(settlement_result, dict)
            and isinstance(settlement_result.get("matches"), list)
            else 0,
        ) if isinstance(settlement_result, dict) else 0,
        "statement_balanced": balance_result.get(
            "statement_balanced"
        ) if isinstance(balance_result, dict) else None,
        "exception_count": len(output["exceptions"]),
        "writes_performed": False,
    }

    # Engine failures are reported without hiding successful results.
    failed_engines = [
        name
        for name, result in output["engines"].items()
        if isinstance(result, dict)
        and result.get("success") is False
    ]

    output["failed_engines"] = failed_engines

    if failed_engines:
        output["success"] = False
        output["message"] = (
            "Reconciliation completed with one or more engine errors. "
            "Inspect failed_engines and individual engine results."
        )
    else:
        output["message"] = (
            "Unified reconciliation completed in dry-run mode. "
            "Review proposed matches and exceptions before confirmation."
        )

    return output
    
# ============================================================
# DATABASE-INTEGRATED RECONCILIATION ENTRY POINT
# ============================================================

from mysql_pipeline.transaction_storage import list_user_transactions
from mysql_pipeline.account_storage import list_user_accounts


def reconcile_user_from_database(
    user_id,
    transaction_limit=1000,
    max_transfer_date_gap_days=2,
    max_refund_date_gap_days=90,
):
    """
    Fetch a user's stored transactions and accounts,
    then run all existing reconciliation engines.

    DRY RUN:
    - Does not modify transactions.
    - Does not create reconciliation cases.
    - Does not confirm or reject matches.
    """

    if isinstance(user_id, bool) or not isinstance(user_id, int) or user_id <= 0:
        return {"success": False, "message": "Invalid user_id."}

    # 1. Retrieve stored transactions
    transaction_result = list_user_transactions(
        user_id,
        limit=transaction_limit,
        offset=0,
    )

    if not transaction_result.get("success"):
        return {
            "success": False,
            "stage": "transaction_retrieval",
            "message": transaction_result.get("message"),
        }

    transactions = transaction_result.get("transactions", [])

    if not transactions:
        return {
            "success": False,
            "stage": "transaction_retrieval",
            "message": "No transactions found.",
        }

    # 2. Retrieve account metadata
    account_result = list_user_accounts(user_id)

    if not account_result.get("success"):
        return {
            "success": False,
            "stage": "account_retrieval",
            "message": account_result.get("message"),
        }

    account_rows = account_result.get("accounts", [])

    # 3. Prepare verified account metadata and associate currency
    account_map = {account["account_id"]: account for account in account_rows}
    default_acc_id = account_rows[0]["account_id"] if account_rows else None

    for tx in transactions:
        if not tx.get("account_id") and default_acc_id:
            tx["account_id"] = default_acc_id
        acc = account_map.get(tx.get("account_id"))
        if acc and not tx.get("currency"):
            tx["currency"] = acc.get("currency", "INR")
        elif not tx.get("currency"):
            tx["currency"] = "INR"

    accounts = {
        account["account_id"]: {
            **account,
            "verified": True,
        }
        for account in account_rows
    }

    # 4. Run the existing reconciliation coordinator
    result = reconcile_all_transactions(
        transactions,
        accounts=accounts,
        max_transfer_date_gap_days=max_transfer_date_gap_days,
        max_refund_date_gap_days=max_refund_date_gap_days,
    )

    # 5. Return unified result
    return {
        "success": result.get("success", False),
        "user_id": user_id,
        "mode": "database_dry_run",
        "transactions_retrieved": len(transactions),
        "accounts_retrieved": len(account_rows),
        "reconciliation": result,
        "writes_performed": False,
    }
