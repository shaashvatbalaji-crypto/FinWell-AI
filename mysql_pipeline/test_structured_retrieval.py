
from mysql_pipeline.structured_retrieval_service import (
    get_structured_financial_data,
    get_financial_overview,
    get_transaction_overview,
    get_reconciliation_overview,
)

TEST_USER_ID = 1


def print_result(title, result):
    print("\n" + "=" * 65)
    print(title)
    print("=" * 65)

    print("Overall success:", result["success"])
    print("User ID:", result["user_id"])
    print("Section status:", result["section_status"])

    for section, data in result["data"].items():
        print(f"\n{section}:")
        print("  Success:", data.get("success"))


if __name__ == "__main__":

    # Test 1: All six sections
    result = get_structured_financial_data(
        user_id=TEST_USER_ID
    )

    print_result(
        "COMPLETE STRUCTURED RETRIEVAL",
        result,
    )

    # Test 2: Financial overview
    overview = get_financial_overview(
        TEST_USER_ID
    )

    print_result(
        "FINANCIAL OVERVIEW",
        overview,
    )

    # Test 3: Transaction overview
    transactions = get_transaction_overview(
        TEST_USER_ID,
        limit=10,
    )

    print_result(
        "TRANSACTION OVERVIEW",
        transactions,
    )

    # Test 4: Reconciliation overview
    reconciliation = get_reconciliation_overview(
        TEST_USER_ID
    )

    print_result(
        "RECONCILIATION OVERVIEW",
        reconciliation,
    )
