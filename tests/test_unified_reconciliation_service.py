
from reconciliation import unified_reconciliation_service as unified


def test_all_engines_run_and_results_are_aggregated(monkeypatch):
    transactions = [
        {
            "transaction_id": 101,
            "user_id": 1,
            "account_id": 10,
            "date": "2026-11-05",
            "description": "AMAZON PURCHASE REF A501",
            "debit": 3000,
            "credit": 0,
            "balance": 47000,
        },
        {
            "transaction_id": 102,
            "user_id": 1,
            "account_id": 10,
            "date": "2026-11-10",
            "description": "AMAZON REFUND REF A501",
            "debit": 0,
            "credit": 1000,
            "balance": 48000,
        },
    ]

    existing = [{
        "transaction_id": 90,
        "user_id": 1,
        "account_id": 10,
        "date": "2026-11-05",
        "description": "AMAZON PURCHASE REF A501",
        "debit": 3000,
        "credit": 0,
    }]

    duplicate_result = {
        "is_candidate": True,
        "match_type": "duplicate",
        "confidence_score": 0.98,
        "match_reason": "Test duplicate",
    }

    monkeypatch.setattr(
        unified,
        "detect_duplicate_candidate",
        lambda a, b: duplicate_result,
    )

    monkeypatch.setattr(
        unified,
        "reconcile_internal_transfers",
        lambda *args, **kwargs: {
            "success": True,
            "candidates": [{"transaction_id": 101}],
            "unmatched_candidates": [],
            "review_required": [],
        },
    )

    monkeypatch.setattr(
        unified,
        "reconcile_refunds",
        lambda *args, **kwargs: {
            "success": True,
            "allocation_count": 1,
            "allocations": [{"amount": "1000.00"}],
            "review": [],
            "unmatched_refunds": [],
            "over_refunds": [],
            "invalid_transaction_ids": [],
        },
    )

    monkeypatch.setattr(
        unified,
        "reconcile_settlements",
        lambda *args, **kwargs: {
            "success": True,
            "matches": [{"settlement_id": "SET001"}],
            "candidate_count": 1,
        },
    )

    monkeypatch.setattr(
        unified,
        "reconcile_statement_balance",
        lambda *args, **kwargs: {
            "success": True,
            "statement_balanced": True,
            "invalid_transactions": [],
            "running_balance_mismatches": [],
        },
    )

    result = unified.reconcile_all_transactions(
        transactions,
        existing_transactions=existing,
        accounts={
            10: {"user_id": 1, "verified": True},
            20: {"user_id": 1, "verified": True},
        },
        gateway_transactions=[{"transaction_id": 201}],
        bank_transactions=[{"transaction_id": 202}],
        opening_balance=50000,
        closing_balance=48000,
    )

    assert result["success"] is True
    assert result["mode"] == "dry_run"
    assert result["writes_performed"] is False
    assert result["original_transactions_modified"] is False

    # 2 incoming x 1 existing + 1 incoming pair = 3 comparisons.
    assert result["summary"]["duplicate_comparison_count"] == 3
    assert result["summary"]["duplicate_candidate_count"] == 3

    assert result["summary"]["transfer_candidate_count"] == 1
    assert result["summary"]["refund_allocation_count"] == 1
    assert result["summary"]["settlement_candidate_count"] == 1
    assert result["summary"]["statement_balanced"] is True

    assert result["failed_engines"] == []


def test_optional_engines_are_skipped_when_inputs_missing(monkeypatch):
    monkeypatch.setattr(
        unified,
        "reconcile_refunds",
        lambda *args, **kwargs: {
            "success": True,
            "allocation_count": 0,
        },
    )

    result = unified.reconcile_all_transactions([
        {
            "transaction_id": 1,
            "date": "2026-11-05",
            "description": "TEST PURCHASE",
            "debit": 100,
            "credit": 0,
        }
    ])

    assert result["success"] is True

    assert (
        result["engines"]["internal_transfers"]["status"]
        == "skipped"
    )

    assert (
        result["engines"]["settlements"]["status"]
        == "skipped"
    )

    assert (
        result["engines"]["balance"]["status"]
        == "skipped"
    )


def test_engine_failure_does_not_stop_other_engines(monkeypatch):
    def failing_refund_engine(*args, **kwargs):
        raise RuntimeError("Simulated refund engine failure")

    monkeypatch.setattr(
        unified,
        "reconcile_refunds",
        failing_refund_engine,
    )

    result = unified.reconcile_all_transactions([
        {
            "transaction_id": 1,
            "date": "2026-11-05",
            "description": "TEST PURCHASE",
            "debit": 100,
            "credit": 0,
        }
    ])

    assert result["success"] is False
    assert "refunds" in result["failed_engines"]

    assert result["engines"]["refunds"]["success"] is False

    assert any(
        item["exception_type"] == "engine_error"
        for item in result["exceptions"]
    )


def test_invalid_transaction_input_is_rejected():
    result = unified.reconcile_all_transactions(
        "not-a-transaction-list"
    )

    assert result["success"] is False
    assert result["writes_performed"] is False


def test_non_dictionary_transaction_is_rejected():
    result = unified.reconcile_all_transactions([
        {"transaction_id": 1},
        "invalid transaction",
    ])

    assert result["success"] is False
    assert result["invalid_input_indexes"] == [1]
