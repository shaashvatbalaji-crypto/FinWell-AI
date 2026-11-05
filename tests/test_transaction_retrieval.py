from mysql_pipeline.transaction_storage import (
    list_document_transactions,
    save_transactions,
)


def run_test():
    user_id = 1
    document_id = 1

    print("\n1. Test bulk transaction insertion")

    sample_transactions = [
        {
            "transaction_date": "2026-10-16",
            "description": "TEST - Transport",
            "debit": 250.00,
            "credit": 0.00,
            "balance": 8500.00,
        },
        {
            "transaction_date": "2026-10-17",
            "description": "TEST - Salary credit",
            "debit": 0.00,
            "credit": 15000.00,
            "balance": 23500.00,
        },
    ]

    result = save_transactions(
        user_id=user_id,
        document_id=document_id,
        transactions=sample_transactions,
    )

    print(result)

    if result["success"]:
        print("PASS: Bulk transaction insertion.")
    else:
        print("FAIL: Bulk transaction insertion.")

    print("\n2. Test transaction retrieval")

    result = list_document_transactions(
        document_id=document_id,
        user_id=user_id,
    )

    print(result)

    if result["success"]:
        print("PASS: Transaction retrieval.")
    else:
        print("FAIL: Transaction retrieval.")


if __name__ == "__main__":
    run_test()