
from reconciliation.duplicate_detector import detect_duplicate_candidate


def make_transaction(
    transaction_id,
    document_id,
    description,
    transaction_date,
    debit=0,
    credit=0,
    user_id=1
):
    """Create a transaction dictionary for testing."""

    return {
        "transaction_id": transaction_id,
        "user_id": user_id,
        "document_id": document_id,
        "transaction_date": transaction_date,
        "description": description,
        "debit": debit,
        "credit": credit
    }


def run_edge_case_tests():

    passed = 0
    total = 7

    print("=" * 65)
    print("TRANSACTION DUPLICATE DETECTOR - EDGE CASE TESTS")
    print("=" * 65)

    # --------------------------------------------------
    # CASE 1: Identical transaction across two documents
    # --------------------------------------------------

    t1 = make_transaction(
        transaction_id=101,
        document_id=10,
        description="POS PURCHASE FRESHBASKET MART CHENNAI",
        transaction_date="2026-10-03",
        debit="2846.50"
    )

    t2 = make_transaction(
        transaction_id=201,
        document_id=11,
        description="POS PURCHASE FRESHBASKET MART CHENNAI",
        transaction_date="2026-10-03",
        debit="2846.50"
    )

    result = detect_duplicate_candidate(t1, t2)

    print("\nCASE 1: Identical cross-document transaction")
    print("Result:", result)

    assert result["is_candidate"] is True
    print("PASS: Identical transaction detected.")
    passed += 1

    # --------------------------------------------------
    # CASE 2: Same transaction, different description order
    # --------------------------------------------------

    t3 = make_transaction(
        transaction_id=202,
        document_id=11,
        description="FRESH BASKET MART CHENNAI POS PURCHASE",
        transaction_date="2026-10-03",
        debit="2846.50"
    )

    result = detect_duplicate_candidate(t1, t3)

    print("\nCASE 2: Different description format")
    print("Result:", result)

    assert result["is_candidate"] is True
    print("PASS: Reordered merchant description detected.")
    passed += 1

    # --------------------------------------------------
    # CASE 3: Same merchant and amount, different purchases
    # --------------------------------------------------

    t4 = make_transaction(
        transaction_id=301,
        document_id=10,
        description="UPI/DR/627233451892/QUICKBITE FOODS/DINNER ORDER",
        transaction_date="2026-10-08",
        debit="486.00"
    )

    t5 = make_transaction(
        transaction_id=302,
        document_id=11,
        description="UPI/DR/627654300981/QUICKBITE FOODS/LUNCH ORDER",
        transaction_date="2026-10-08",
        debit="486.00"
    )

    result = detect_duplicate_candidate(t4, t5)

    print("\nCASE 3: Same merchant, different purchases")
    print("Result:", result)

    assert result["is_candidate"] is False
    print("PASS: Lunch and dinner transactions were distinguished.")
    passed += 1

    # --------------------------------------------------
    # CASE 4: Different transaction amounts
    # --------------------------------------------------

    t6 = make_transaction(
        transaction_id=401,
        document_id=11,
        description="POS PURCHASE FRESHBASKET MART CHENNAI",
        transaction_date="2026-10-03",
        debit="1732.25"
    )

    result = detect_duplicate_candidate(t1, t6)

    print("\nCASE 4: Different transaction amounts")
    print("Result:", result)

    assert result["is_candidate"] is False
    print("PASS: Different amounts rejected.")
    passed += 1

    # --------------------------------------------------
    # CASE 5: Opposite debit and credit directions
    # --------------------------------------------------

    t7 = make_transaction(
        transaction_id=501,
        document_id=11,
        description="POS PURCHASE FRESHBASKET MART CHENNAI",
        transaction_date="2026-10-03",
        credit="2846.50"
    )

    result = detect_duplicate_candidate(t1, t7)

    print("\nCASE 5: Opposite transaction directions")
    print("Result:", result)

    assert result["is_candidate"] is False
    print("PASS: Opposite debit/credit directions rejected.")
    passed += 1

    # --------------------------------------------------
    # CASE 6: Different users
    # --------------------------------------------------

    t8 = make_transaction(
        transaction_id=601,
        document_id=12,
        description="POS PURCHASE FRESHBASKET MART CHENNAI",
        transaction_date="2026-10-03",
        debit="2846.50",
        user_id=2
    )

    result = detect_duplicate_candidate(t1, t8)

    print("\nCASE 6: Different users")
    print("Result:", result)

    assert result["is_candidate"] is False
    print("PASS: Transactions belonging to different users rejected.")
    passed += 1

    # --------------------------------------------------
    # CASE 7: Transaction dates too far apart
    # --------------------------------------------------

    t9 = make_transaction(
        transaction_id=701,
        document_id=11,
        description="POS PURCHASE FRESHBASKET MART CHENNAI",
        transaction_date="2026-10-10",
        debit="2846.50"
    )

    result = detect_duplicate_candidate(t1, t9)

    print("\nCASE 7: Transaction dates too far apart")
    print("Result:", result)

    assert result["is_candidate"] is False
    print("PASS: Transactions more than two days apart rejected.")
    passed += 1

    # --------------------------------------------------
    # FINAL TEST SUMMARY
    # --------------------------------------------------

    print("\n" + "=" * 65)
    print("EDGE CASE TEST SUMMARY")
    print("=" * 65)

    print(f"Total test cases : {total}")
    print(f"Passed           : {passed}")
    print(f"Failed           : {total - passed}")

    if passed == total:
        print("\nALL EDGE CASE TESTS PASSED!")
    else:
        print("\nSOME TESTS FAILED!")

    assert passed == total


if __name__ == "__main__":
    run_edge_case_tests()
