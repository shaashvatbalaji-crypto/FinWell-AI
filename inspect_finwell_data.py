import json
from mysql_pipeline.structured_retrieval_service import get_structured_financial_data

user_id = int(input("Enter user ID: "))

result = get_structured_financial_data(
    user_id=user_id,
    include=["analytics", "transactions"],
    transaction_limit=100,
    reconciliation_limit=100,
    case_limit=50,
)

print("\n========== MYSQL STRUCTURED DATA ==========")
print(json.dumps(result, indent=2, default=str, ensure_ascii=False))
