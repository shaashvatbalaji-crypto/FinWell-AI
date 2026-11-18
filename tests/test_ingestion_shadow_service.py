
from unittest.mock import patch

from reconciliation.ingestion_shadow_service import (
    analyze_incoming_transactions,
)


USER_ID = 3
DOCUMENT_ID = 13
ACCOUNT_ID = 5


def make_transaction(
    date="2026-11-06",
    description="UPI PAYMENT TO AMAZON REF A501",
    debit=3000.00,
    credit=None,
):
    return {
        "date": date,
        "description": description,
        "debit": debit,
        "credit": credit,
    }


def test_missing_account_skips_analysis():
    result = analyze_incoming_transactions(
        user_id=USER_ID,
        document_id=DOCUMENT_ID,
        account_id=None,
        transactions=[make_transaction()],
    )

    assert result["success"] is True
    assert result["skipped"] is True
    assert result["read_only"] is True
    assert result["duplicate_candidate_count"] == 0


@patch(
    "reconciliation.ingestion_shadow_service."
    "_fetch_account_transactions"
)
def test_no_existing_transactions(mock_fetch):
    mock_fetch.return_value = []

    result = analyze_incoming_transactions(
        user_id=USER_ID,
        document_id=DOCUMENT_ID,
        account_id=ACCOUNT_ID,
        transactions=[
            make_transaction(),
            make_transaction(
                date="2026-11-07",
                description="UPI PAYMENT TO FOOD STORE REF B202",
                debit=500.00,
            ),
        ],
    )

    assert result["success"] is True
    assert result["read_only"] is True
    assert result["existing_transaction_count"] == 0
    assert result["pairs_checked"] == 1
    assert result["duplicate_candidate_count"] == 0


@patch(
    "reconciliation.ingestion_shadow_service."
    "_fetch_account_transactions"
)
def test_existing_transactions_are_compared(mock_fetch):
    mock_fetch.return_value = [
        {
            "transaction_id": 500,
            "user_id": USER_ID,
            "document_id": 10,
            "account_id": ACCOUNT_ID,
            "transaction_date": "2026-11-06",
            "description": "UPI PAYMENT TO AMAZON REF A501",
            "debit": 3000.00,
            "credit": None,
        }
    ]

    result = analyze_incoming_transactions(
        user_id=USER_ID,
        document_id=DOCUMENT_ID,
        account_id=ACCOUNT_ID,
        transactions=[make_transaction()],
    )

    assert result["success"] is True
    assert result["existing_transaction_count"] == 1
    assert result["pairs_checked"] == 1

    # A candidate may or may not be produced by the existing
    # production detector. This test checks the adapter and
    # comparison path, not the detector's scoring outcome.
    assert isinstance(result["candidates"], list)


@patch(
    "reconciliation.ingestion_shadow_service."
    "_fetch_account_transactions"
)
def test_database_failure_does_not_raise(mock_fetch):
    mock_fetch.side_effect = RuntimeError("Mock database failure")

    result = analyze_incoming_transactions(
        user_id=USER_ID,
        document_id=DOCUMENT_ID,
        account_id=ACCOUNT_ID,
        transactions=[make_transaction()],
    )

    assert result["success"] is False
    assert result["read_only"] is True
    assert "Mock database failure" in result["message"]


def test_empty_transactions():
    result = analyze_incoming_transactions(
        user_id=USER_ID,
        document_id=DOCUMENT_ID,
        account_id=ACCOUNT_ID,
        transactions=[],
    )

    assert result["success"] is True
    assert result["incoming_transaction_count"] == 0
    assert result["duplicate_candidate_count"] == 0
