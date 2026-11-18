
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from reconciliation.duplicate_detector import detect_duplicate_candidate


def make_transaction(
    transaction_id,
    document_id,
    account_id,
    reference,
):
    return {
        "transaction_id": transaction_id,
        "user_id": 999999,
        "document_id": document_id,
        "account_id": account_id,
        "transaction_date": "2026-11-12",
        "description": f"UPI FRESH BASKET MART REF {reference}",
        "debit": 1250.00,
        "credit": None,
    }


def main():
    print("=" * 65)
    print("FINWELL AI - PRODUCTION DUPLICATE POSITIVE TEST")
    print("=" * 65)

    # Same genuine transaction appearing in two documents.
    original = make_transaction(
        1001, 9001, "TEST_ACCOUNT_4821", "DUP501"
    )

    duplicate = make_transaction(
        1002, 9002, "TEST_ACCOUNT_4821", "DUP501"
    )

    result = detect_duplicate_candidate(original, duplicate)

    print("\nTEST 1: Genuine duplicate across documents")
    print("Candidate:", result.get("is_candidate"))
    print("Confidence:", result.get("confidence_score"))

    assert result["is_candidate"] is True, (
        "FAIL: Genuine duplicate was not detected."
    )

    print("PASS: Genuine duplicate identified.")

    # Same amount/date/merchant, but different reference.
    different_reference = make_transaction(
        1003, 9003, "TEST_ACCOUNT_4821", "OTHER999"
    )

    result_reference = detect_duplicate_candidate(
        original, different_reference
    )

    print("\nTEST 2: Different transaction reference")
    print("Candidate:", result_reference.get("is_candidate"))

    if result_reference.get("is_candidate"):
        print(
            "WARNING: Different references are still being "
            "considered duplicate candidates."
        )
    else:
        print("PASS: Different reference rejected.")

    # Same transaction details, but different accounts.
    different_account = make_transaction(
        1004, 9004, "TEST_ACCOUNT_7392", "DUP501"
    )

    result_account = detect_duplicate_candidate(
        original, different_account
    )

    print("\nTEST 3: Different account")
    print("Candidate:", result_account.get("is_candidate"))

    if result_account.get("is_candidate"):
        print(
            "WARNING: Different accounts are still being "
            "considered duplicate candidates."
        )
    else:
        print("PASS: Different account rejected.")

    print("\n" + "=" * 65)
    print("POSITIVE DUPLICATE TEST COMPLETED")
    print("No MySQL writes.")
    print("No ChromaDB writes.")
    print("No production code modified.")
    print("=" * 65)


if __name__ == "__main__":
    main()
