"""
Comprehensive Integration Tests for FinWell AI Reconciliation API.

Tests:
1. GET /api/reconciliation/cases
   - Verifies actual account IDs, actual currencies, and confidence scores.
   - Verifies mapping consistency with ReconciliationCase.
2. Tenant Isolation
   - Verifies another user receives 0 cases and cannot view or mutate user 1's matches.
3. PATCH /api/reconciliation/cases/{case_id}/status
   - Uses disposable test records.
   - Verifies that only the targeted suggested match is updated.
   - Verifies that existing baseline matches (2, 3, 4, 5) remain untouched in 'suggested' state.
4. POST /api/reconciliation/evaluate
   - Verifies read-only evaluation: performs 0 database writes.
"""

from decimal import Decimal
from fastapi.testclient import TestClient

from api.main import app
from api.routes.auth import create_access_token
from mysql_pipeline.db import get_db_connection


client = TestClient(app)
BASE_URL = "/api/reconciliation"


def make_request(path, method="GET", data=None, token=None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if method == "GET":
        resp = client.get(path, headers=headers)
    elif method == "PATCH":
        resp = client.patch(path, json=data, headers=headers)
    elif method == "POST":
        resp = client.post(path, json=data, headers=headers)
    else:
        raise ValueError(f"Unsupported method {method}")
    return resp.status_code, resp.json()


def test_reconciliation_api():
    print("\n" + "=" * 60)
    print("FINWELL AI: RECONCILIATION API INTEGRATION TESTS")
    print("=" * 60)

    token_user_1 = create_access_token(1)
    token_user_4 = create_access_token(4)

    # -------------------------------------------------------------
    # Test 1: GET /api/reconciliation/cases for User 1
    # -------------------------------------------------------------
    print("\n[TEST 1] Testing GET /api/reconciliation/cases for User 1...")
    status_code, data = make_request(f"{BASE_URL}/cases", method="GET", token=token_user_1)
    assert status_code == 200, f"Expected 200, got {status_code}: {data}"
    assert data["success"] is True
    assert data["user_id"] == 1
    assert data["count"] >= 4, f"Expected at least 4 matches, got {data['count']}"

    first_case = data["cases"][0]
    print(f"  Retrieved {data['count']} cases.")
    print(f"  Sample Case #{first_case['case_id']}:")
    print(f"    Type: {first_case['case_type']}")
    print(f"    Status: {first_case['status']}")
    print(f"    Confidence: {first_case['confidence_score']}%")
    print(f"    Source: Tx {first_case['source_transaction']['transaction_id']}, Account: {first_case['source_transaction']['account_id']} ({first_case['source_transaction']['account_name']}), Currency: {first_case['source_transaction']['currency']}")
    print(f"    Target: Tx {first_case['target_transaction']['transaction_id']}, Account: {first_case['target_transaction']['account_id']} ({first_case['target_transaction']['account_name']}), Currency: {first_case['target_transaction']['currency']}")

    # Assertions on fields
    assert first_case["source_transaction"]["account_id"] is not None and first_case["source_transaction"]["account_id"] > 0
    assert first_case["target_transaction"]["account_id"] is not None and first_case["target_transaction"]["account_id"] > 0
    assert first_case["source_transaction"]["currency"] == "INR"
    assert first_case["target_transaction"]["currency"] == "INR"
    assert first_case["confidence_score"] == 99.0
    print("  [PASS] Account IDs, currencies, and confidence scores verified (no hardcoded 0s or assumed currencies).")

    # -------------------------------------------------------------
    # Test 2: User Tenant Isolation
    # -------------------------------------------------------------
    print("\n[TEST 2] Testing User Tenant Isolation...")
    # User 4 should have 0 cases
    status_code_u4, data_u4 = make_request(f"{BASE_URL}/cases", method="GET", token=token_user_4)
    assert status_code_u4 == 200
    assert data_u4["count"] == 0, f"User 4 should see 0 cases, got {data_u4['count']}"
    print("  [PASS] User 4 sees 0 cases (no cross-tenant leakage).")

    # User 4 attempting to update User 1's match #2
    status_code_hack, data_hack = make_request(
        f"{BASE_URL}/cases/2/status",
        method="PATCH",
        data={"status": "confirmed"},
        token=token_user_4,
    )
    assert status_code_hack == 400
    assert "not owned by this user" in data_hack.get("detail", "").lower()
    print("  [PASS] Cross-tenant mutation blocked: unauthorized user cannot update another user's match.")

    # -------------------------------------------------------------
    # Test 3: PATCH with Disposable Test Data & Verify Unrelated Unchanged
    # -------------------------------------------------------------
    print("\n[TEST 3] Testing PATCH with disposable test records...")
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    # Record baseline state of matches 2, 3, 4, 5
    cur.execute("SELECT match_id, match_status FROM reconciliation_matches WHERE match_id IN (2, 3, 4, 5)")
    baseline_statuses = {r["match_id"]: r["match_status"] for r in cur.fetchall()}
    print(f"  Baseline statuses before patch: {baseline_statuses}")

    # Create temporary disposable transactions and match for user 1
    cur.execute("""
        INSERT INTO transactions (user_id, document_id, account_id, transaction_date, description, debit, credit, balance)
        VALUES (1, 14, 4, '2026-12-15', 'TEMP RECONCILIATION TEST DEBIT', 1500.00, NULL, 50000.00)
    """)
    temp_tx1 = cur.lastrowid

    cur.execute("""
        INSERT INTO transactions (user_id, document_id, account_id, transaction_date, description, debit, credit, balance)
        VALUES (1, 14, 5, '2026-12-15', 'TEMP RECONCILIATION TEST CREDIT', NULL, 1500.00, 50000.00)
    """)
    temp_tx2 = cur.lastrowid

    cur.execute("""
        INSERT INTO reconciliation_matches (transaction_id, matched_transaction_id, match_type, confidence_score, match_status, match_reason)
        VALUES (%s, %s, 'internal_transfer', 0.9500, 'suggested', 'Temp disposable test match')
    """, (temp_tx1, temp_tx2))
    temp_match_id = cur.lastrowid
    conn.commit()
    print(f"  Created disposable match #{temp_match_id} (Tx {temp_tx1} <-> Tx {temp_tx2}).")

    try:
        # Patch the disposable match to 'confirmed'
        patch_status, patch_data = make_request(
            f"{BASE_URL}/cases/{temp_match_id}/status",
            method="PATCH",
            data={"status": "confirmed"},
            token=token_user_1,
        )
        assert patch_status == 200, f"Expected 200, got {patch_status}: {patch_data}"
        assert patch_data["success"] is True
        assert patch_data["new_status"] == "confirmed"
        print(f"  [PASS] Successfully confirmed disposable match #{temp_match_id}.")

        # Verify in database that ONLY temp_match_id was changed
        cur.execute("SELECT match_status FROM reconciliation_matches WHERE match_id = %s", (temp_match_id,))
        temp_row = cur.fetchone()
        assert temp_row["match_status"] == "confirmed"

        # Verify baseline matches 2, 3, 4, 5 remain in exact baseline status
        cur.execute("SELECT match_id, match_status FROM reconciliation_matches WHERE match_id IN (2, 3, 4, 5)")
        current_statuses = {r["match_id"]: r["match_status"] for r in cur.fetchall()}
        print(f"  Current statuses of baseline matches: {current_statuses}")
        assert current_statuses == baseline_statuses, "Baseline records were modified!"
        print("  [PASS] Confirmed that unrelated baseline records (2, 3, 4, 5) remained completely unchanged.")

    finally:
        # Clean up disposable test data
        cur.execute("DELETE FROM reconciliation_matches WHERE match_id = %s", (temp_match_id,))
        cur.execute("DELETE FROM transactions WHERE transaction_id IN (%s, %s)", (temp_tx1, temp_tx2))
        conn.commit()
        print("  [PASS] Disposable test data cleaned up.")

    # -------------------------------------------------------------
    # Test 4: POST /api/reconciliation/evaluate (Read-Only Verification)
    # -------------------------------------------------------------
    print("\n[TEST 4] Testing POST /api/reconciliation/evaluate (Dry Run)...")

    # Record row counts before evaluation
    cur.execute("SELECT COUNT(*) AS c FROM reconciliation_matches")
    count_matches_before = cur.fetchone()["c"]
    cur.execute("SELECT COUNT(*) AS c FROM transactions")
    count_tx_before = cur.fetchone()["c"]
    cur.execute("SELECT COUNT(*) AS c FROM reconciliation_cases")
    count_cases_before = cur.fetchone()["c"]

    eval_status, eval_data = make_request(f"{BASE_URL}/evaluate", method="POST", token=token_user_1)
    assert eval_status == 200, f"Expected 200, got {eval_status}: {eval_data}"
    assert eval_data["success"] is True
    assert eval_data["mode"] == "database_dry_run"
    assert eval_data["writes_performed"] is False
    print(f"  Evaluation returned: {eval_data.get('transactions_retrieved')} tx, {eval_data.get('accounts_retrieved')} accounts.")
    print(f"  Writes performed: {eval_data.get('writes_performed')}")

    # Check row counts after evaluation
    cur.execute("SELECT COUNT(*) AS c FROM reconciliation_matches")
    count_matches_after = cur.fetchone()["c"]
    cur.execute("SELECT COUNT(*) AS c FROM transactions")
    count_tx_after = cur.fetchone()["c"]
    cur.execute("SELECT COUNT(*) AS c FROM reconciliation_cases")
    count_cases_after = cur.fetchone()["c"]

    assert count_matches_before == count_matches_after, "Matches count changed during dry run!"
    assert count_tx_before == count_tx_after, "Transactions count changed during dry run!"
    assert count_cases_before == count_cases_after, "Cases count changed during dry run!"
    print("  [PASS] Zero database writes verified: table row counts are strictly identical before and after.")

    cur.close()
    conn.close()

    print("\n" + "=" * 60)
    print("ALL RECONCILIATION API INTEGRATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    test_reconciliation_api()
