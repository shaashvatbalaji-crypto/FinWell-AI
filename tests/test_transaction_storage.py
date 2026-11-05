from mysql_pipeline.transaction_storage import save_transaction


def run_test():
    result = save_transaction(
        user_id=1,
        document_id=1,
        transaction_date="2026-10-15",
        description="TEST - Grocery purchase",
        debit=1250.00,
        credit=0.00,
        balance=8750.00,
    )

    print("Transaction storage result:", result)

    if result["success"]:
        print("PASS: Transaction was saved.")
    else:
        print("FAIL:", result["message"])


if __name__ == "__main__":
    run_test()