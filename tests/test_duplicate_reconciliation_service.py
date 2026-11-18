
from reconciliation.duplicate_reconciliation_service import (
    run_duplicate_reconciliation
)


def test_duplicate_reconciliation_dry_run():

    result = run_duplicate_reconciliation(
        user_id=1,
        dry_run=True
    )

    print("\n========== DUPLICATE RECONCILIATION ==========")

    print("Success:", result["success"])
    print("User ID:", result["user_id"])
    print("Total transactions:", result["total_transactions"])
    print("Pairs checked:", result["total_pairs_checked"])
    print("Candidates found:", result["candidate_count"])
    print("Dry run:", result["dry_run"])

    for candidate in result.get("candidates", []):

        print("\n--------------------------------")
        print(
            "Transaction:",
            candidate["transaction_id"]
        )
        print(
            "Matched transaction:",
            candidate["matched_transaction_id"]
        )
        print(
            "Confidence:",
            candidate["confidence_score"]
        )
        print(
            "Description similarity:",
            candidate["description_similarity"]
        )
        print(
            "Reason:",
            candidate["match_reason"]
        )
        print(
            "Storage:",
            candidate["storage_status"]
        )

    assert result["success"] is True
    assert result["dry_run"] is True
    assert result["saved_count"] == 0

    print("\nDRY-RUN TEST PASSED!")
    print("No reconciliation matches were inserted.")


if __name__ == "__main__":
    test_duplicate_reconciliation_dry_run()
