
from reconciliation.multi_account_reconciler import (
    reconcile_multiple_accounts,
)

transactions = [
    # Account 4821 — November primary statement
    {"account_id": "4821", "date": "2026-11-02", "description": "SALARY CREDIT", "credit": 40000, "debit": None},
    {"account_id": "4821", "date": "2026-11-03", "description": "SWIGGY S102", "debit": 450, "credit": None},
    {"account_id": "4821", "date": "2026-11-05", "description": "AMAZON PURCHASE", "debit": 3000, "credit": None},
    {"account_id": "4821", "date": "2026-11-06", "description": "UPI TRANSFER TO OWN AC 7392 REF TRF501 MC2606NOV482104", "debit": 5000, "credit": None},
    {"account_id": "4821", "date": "2026-11-08", "description": "BIGBASKET", "debit": 1200, "credit": None},
    {"account_id": "4821", "date": "2026-11-10", "description": "AMAZON REFUND A501", "credit": 1000, "debit": None},
    {"account_id": "4821", "date": "2026-11-12", "description": "NETFLIX", "debit": 199, "credit": None},
    {"account_id": "4821", "date": "2026-11-14", "description": "AMAZON REFUND A501", "credit": 500, "debit": None},
    {"account_id": "4821", "date": "2026-11-15", "description": "UPI PAYMENT", "debit": 2000, "credit": None},
    {"account_id": "4821", "date": "2026-11-18", "description": "SWIGGY S102", "debit": 450, "credit": None},
    {"account_id": "4821", "date": "2026-11-20", "description": "ELECTRICITY", "debit": 1500, "credit": None},
    {"account_id": "4821", "date": "2026-11-22", "description": "CASHBACK", "credit": 100, "debit": None},
    {"account_id": "4821", "date": "2026-11-25", "description": "UPI PAYMENT", "debit": 2000, "credit": None},
    {"account_id": "4821", "date": "2026-11-28", "description": "INTEREST", "credit": 50, "debit": None},

    # Account 7392 — November secondary statement
    {"account_id": "7392", "date": "2026-11-06", "description": "UPI RECEIVED FROM OWN AC 4821 REF TRF501 MC2606NOV739201", "credit": 5000, "debit": None},
    {"account_id": "7392", "date": "2026-11-09", "description": "ATM CASH WITHDRAWAL", "debit": 1000, "credit": None},
    {"account_id": "7392", "date": "2026-11-13", "description": "FREELANCE INCOME", "credit": 8000, "debit": None},
    {"account_id": "7392", "date": "2026-11-17", "description": "RESTAURANT", "debit": 750, "credit": None},
    {"account_id": "7392", "date": "2026-11-21", "description": "ONLINE PURCHASE", "debit": 1200, "credit": None},
]

# Supply the currency explicitly.
for tx in transactions:
    tx["currency"] = "INR"

result = reconcile_multiple_accounts(transactions)

print("\n========== NOVEMBER MULTI-ACCOUNT TEST ==========")
print("Success:", result["success"])
print("Summary:", result["summary"])

for account in result["account_reports"]:
    print("\nAccount:", account["account_id"])
    print("Transactions:", account["transaction_count"])
    print("External income:", account["external_income"])
    print("External expenses:", account["external_expenses"])
    print("Internal transfer debits:", account["internal_transfer_debits"])
    print("Internal transfer credits:", account["internal_transfer_credits"])

consolidated = result["consolidated_report"]["INR"]

print("\n========== CONSOLIDATED REPORT ==========")
for key, value in consolidated.items():
    print(f"{key}: {value}")

print("\n========== TRANSFER MATCHES ==========")
for match in result["transfer_reconciliation"]["matches"]:
    print(
        match["reference"],
        match["amount"],
        match["debit_account_id"],
        "->",
        match["credit_account_id"],
    )

# Assertions
assert result["success"] is True
assert result["summary"]["total_accounts"] == 2
assert result["summary"]["total_transactions"] == 19
assert result["summary"]["matched_internal_transfer_pairs"] == 1

assert consolidated["external_income"] == 49650.00
assert consolidated["external_expenses"] == 13749.00
assert consolidated["internal_transfer_debits"] == 5000.00
assert consolidated["internal_transfer_credits"] == 5000.00

assert len(result["transfer_reconciliation"]["matches"]) == 1
assert result["transfer_reconciliation"]["matches"][0]["reference"] == "TRF501"

assert result["summary"]["unmatched_transfer_candidates"] == 0

print("\nALL NOVEMBER MULTI-ACCOUNT ASSERTIONS PASSED!")
