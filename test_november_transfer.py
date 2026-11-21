from reconciliation.inter_account_reconciler import (
    match_inter_account_transfers,
)

transactions = [
    {
        "account_id": "4821",
        "date": "2026-11-06",
        "description": (
            "UPI TRANSFER TO OWN AC 7392 "
            "REF TRF501 MC2606NOV482104"
        ),
        "debit": 5000.00,
        "credit": None,
        "currency": "INR",
    },
    {
        "account_id": "7392",
        "date": "2026-11-06",
        "description": (
            "UPI RECEIVED FROM OWN AC 4821 "
            "REF TRF501 MC2606NOV739201"
        ),
        "debit": None,
        "credit": 5000.00,
        "currency": "INR",
    },
]

result = match_inter_account_transfers(transactions)

print("\n========== NOVEMBER TRF501 TEST ==========")
print("Success:", result["success"])
print("Matches:", len(result["matches"]))
print("Unmatched:", len(result["unmatched_transactions"]))
print("Ambiguous:", len(result["ambiguous_transactions"]))
print("Summary:", result["summary"])

for match in result["matches"]:
    print("\nMATCH FOUND")
    print("Reference:", match["reference"])
    print("Amount:", match["amount"])
    print("Debit account:", match["debit_account_id"])
    print("Credit account:", match["credit_account_id"])

assert result["success"]
assert len(result["matches"]) == 1
assert result["matches"][0]["reference"] == "TRF501"
assert result["matches"][0]["amount"] == 5000.00
assert result["matches"][0]["debit_account_id"] == "4821"
assert result["matches"][0]["credit_account_id"] == "7392"
assert len(result["unmatched_transactions"]) == 0
assert len(result["ambiguous_transactions"]) == 0

print("\nALL NOVEMBER TRANSFER ASSERTIONS PASSED!")