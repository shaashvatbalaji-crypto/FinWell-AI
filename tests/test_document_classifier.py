from pdf_extraction.document_classifier import classify_document


# Test 1: Bank statement
bank_text = """
BANK STATEMENT
Account Number: 123456789
Opening Balance: 10000.00
Closing Balance: 12500.00
Transaction Date: 01-11-2026
"""

result = classify_document(bank_text)

print("TEST 1: Bank statement")
print(result)

assert result["success"] is True
assert result["document_type"] == "bank_statement"


# Test 2: Credit card statement
card_text = """
CREDIT CARD STATEMENT
Credit Limit: 100000
Total Amount Due: 12500
Minimum Amount Due: 1500
"""

result = classify_document(card_text)

print("\nTEST 2: Credit card statement")
print(result)

assert result["document_type"] == "credit_card_statement"


# Test 3: Loan agreement
loan_text = """
LOAN AGREEMENT
Loan Amount: 500000
Interest Rate: 9.5%
Repayment Schedule
Monthly EMI: 10500
"""

result = classify_document(loan_text)

print("\nTEST 3: Loan agreement")
print(result)

assert result["document_type"] == "loan_agreement"


# Test 4: Unknown document
unknown_text = """
This document contains general information
about a meeting and its schedule.
"""

result = classify_document(unknown_text)

print("\nTEST 4: Unknown document")
print(result)

assert result["document_type"] == "unknown"


# Test 5: Empty text
result = classify_document("")

print("\nTEST 5: Empty text")
print(result)

assert result["success"] is False


print("\nAll document classifier tests passed!")