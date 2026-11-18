
from reconciliation.reconciliation_service import reconcile_transaction


def test_reconciliation_service():

    test_transactions = [
        {
            "description": "NEFT CR-NORTHWIND SOFTWARE LABS-SALARY SEP 2026",
            "debit": 0,
            "credit": 78000,
            "expected_merchant": "Northwind Software Labs",
            "expected_type": "income"
        },
        {
            "description": "POS PURCHASE FRESHBASKET MART CHENNAI",
            "debit": 2846.50,
            "credit": 0,
            "expected_merchant": "FreshBasket Mart",
            "expected_type": "expense"
        },
        {
            "description": "UPI/DR/627233451892/QUICKBITE FOODS/DINNER ORDER",
            "debit": 486,
            "credit": 0,
            "expected_merchant": "QuickBite Foods",
            "expected_type": "expense"
        },
        {
            "description": "TRF TO SELF A/C XXXX7788 GOAL SAVINGS REF ITR-1009",
            "debit": 25000,
            "credit": 0,
            "expected_merchant": "Own Account Transfer",
            "expected_type": "transfer"
        }
    ]

    for transaction in test_transactions:

        result = reconcile_transaction(
            user_id=1,
            description=transaction["description"],
            debit=transaction["debit"],
            credit=transaction["credit"]
        )

        print("\nOriginal:", result["original_description"])
        print("Merchant:", result["normalized_merchant"])
        print("Transaction type:", result["transaction_type"])
        print("Category:", result["category"])
        print("Confidence:", result["confidence_score"])
        print("Reason:", result["classification_reason"])

        assert result["success"] is True

        assert (
            result["normalized_merchant"]
            == transaction["expected_merchant"]
        )

        assert (
            result["transaction_type"]
            == transaction["expected_type"]
        )


if __name__ == "__main__":
    test_reconciliation_service()
