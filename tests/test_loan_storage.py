from mysql_pipeline.loan_storage import save_loan


def run_test():
    result = save_loan(
        user_id=1,
        document_id=1,
        lender_name="TEST Bank",
        loan_type="Personal Loan",
        principal_amount=250000.00,
        interest_rate=12.5,
        loan_start_date="2026-01-01",
        loan_end_date="2028-01-01",
        monthly_emi=11800.00,
    )

    print("Loan storage result:", result)

    if result["success"]:
        print("PASS: Loan details saved.")
    else:
        print("FAIL:", result["message"])


if __name__ == "__main__":
    run_test()