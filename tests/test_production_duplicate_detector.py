import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from reconciliation.duplicate_detector import detect_duplicate_candidate


def make_tx(
    transaction_id,
    user_id=1,
    document_id=10,
    transaction_date="2026-11-05",
    description="FRESH BASKET MART PURCHASE REF A501",
    debit="3000.00",
    credit="0.00",
    account_id=101,
):
    return {
        "transaction_id": transaction_id,
        "user_id": user_id,
        "document_id": document_id,
        "transaction_date": transaction_date,
        "description": description,
        "debit": debit,
        "credit": credit,
        # Extra field: the current detector does not inspect this.
        "account_id": account_id,
    }


def run_case(name, tx1, tx2, expected):
    result = detect_duplicate_candidate(tx1, tx2)
    actual = result.get("is_candidate", False)

    assert actual == expected, (
        f"{name}: expected {expected}, got {actual}. Result: {result}"
    )

    print(f"PASS: {name}")
    print(f"      {result}")


def main():
    print("=" * 70)
    print("FINWELL AI - PRODUCTION DUPLICATE DETECTOR TEST")
    print("=" * 70)

    # 1. Exact repeated transaction
    run_case(
        "Exact duplicate",
        make_tx(1),
        make_tx(2),
        True,
    )

    # 2. Same user, different amount
    run_case(
        "Different amount",
        make_tx(3),
        make_tx(4, debit="2500.00"),
        False,
    )

    # 3. Debit versus credit
    run_case(
        "Different transaction direction",
        make_tx(5),
        make_tx(6, debit="0.00", credit="3000.00"),
        False,
    )

    # 4. Different user
    run_case(
        "Cross-user transaction",
        make_tx(7),
        make_tx(8, user_id=2),
        False,
    )

    # 5. Same transaction ID
    run_case(
        "Same transaction ID",
        make_tx(9),
        make_tx(9),
        False,
    )

    # 6. Date difference of two days
    run_case(
        "Two-day date difference",
        make_tx(10),
        make_tx(11, transaction_date="2026-11-07"),
        True,
    )

    # 7. Date difference of three days
    run_case(
        "Three-day date difference",
        make_tx(12),
        make_tx(13, transaction_date="2026-11-08"),
        False,
    )

    # 8. Conflicting recognized merchants
    run_case(
        "Different known merchants",
        make_tx(14, description="FRESH BASKET MART PURCHASE"),
        make_tx(15, description="QUICKBITE FOODS PURCHASE"),
        False,
    )

    # 9. Different important details
    run_case(
        "Conflicting purchase details",
        make_tx(16, description="FRESH BASKET MART LUNCH"),
        make_tx(17, description="FRESH BASKET MART DINNER"),
        False,
    )

    # 10. Same document, insufficient description similarity
    run_case(
        "Same-document weak description similarity",
        make_tx(18, description="ALPHA TRANSACTION"),
        make_tx(19, description="OMEGA TRANSFER"),
        False,
    )

    # 11. Different accounts: detector currently ignores account_id.
    run_case(
        "Different accounts - current detector behaviour",
        make_tx(20, account_id=101),
        make_tx(21, account_id=202),
        True,
    )

    # 12. Different references: detector currently ignores references.
    run_case(
        "Different references - current detector behaviour",
        make_tx(22, description="FRESH BASKET MART PURCHASE REF A501"),
        make_tx(23, description="FRESH BASKET MART PURCHASE REF A999"),
        True,
    )

    print("\n" + "=" * 70)
    print("ALL 12 PRODUCTION DETECTOR BEHAVIOUR TESTS PASSED")
    print("=" * 70)
    print("No database writes.")
    print("No ChromaDB writes.")
    print("Production detector was not modified.")


if __name__ == "__main__":
    main()
