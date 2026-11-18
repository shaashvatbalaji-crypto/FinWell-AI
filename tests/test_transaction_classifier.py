
from reconciliation.transaction_classifier import classify_transaction


def test_transaction_classifier():

    test_cases = [
        {
            "description": "NEFT CR-NORTHWIND SOFTWARE LABS-SALARY",
            "debit": 0,
            "credit": 78000,
            "expected": "income"
        },
        {
            "description": "NACH DR-SUNRISE HOUSING FINANCE-LOAN EMI",
            "debit": 18450,
            "credit": 0,
            "expected": "expense"
        },
        {
            "description": "POS PURCHASE FRESHBASKET MART CHENNAI",
            "debit": 2846.50,
            "credit": 0,
            "expected": "expense"
        },
        {
            "description": "TRF TO SELF A/C XXXX7788",
            "debit": 25000,
            "credit": 0,
            "expected": "transfer"
        },
        {
            "description": "UPI REFUND QUICKBITE FOODS",
            "debit": 0,
            "credit": 398,
            "expected": "refund"
        },
        {
            "description": "UNKNOWN TRANSACTION XYZ",
            "debit": 0,
            "credit": 0,
            "expected": "other"
        }
    ]

    for case in test_cases:

        result = classify_transaction(
            description=case["description"],
            debit=case["debit"],
            credit=case["credit"]
        )

        print("\nDescription:", case["description"])
        print("Type:", result["transaction_type"])
        print("Category:", result["category"])
        print("Confidence:", result["confidence_score"])
        print("Reason:", result["reason"])

        assert result["transaction_type"] == case["expected"]


if __name__ == "__main__":
    test_transaction_classifier()
