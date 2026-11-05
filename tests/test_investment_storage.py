from mysql_pipeline.investment_storage import save_investment


result = save_investment(
    user_id=1,
    document_id=1,
    investment_name="TEST - Index Fund",
    investment_type="Mutual Fund",
    quantity=10,
    purchase_value=5000.00,
    current_value=5500.00,
    investment_date="2026-01-15",
)

print("Investment storage result:", result)

if result["success"]:
    print("PASS: Investment details saved.")
else:
    print("FAIL: Investment details were not saved.")
    