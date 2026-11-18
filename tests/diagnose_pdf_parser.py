import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pdf_extraction.pdf_reader import extract_pdf_text
from preprocessing.text_cleaner import clean_extracted_text
from preprocessing.transaction_parser import parse_transactions

files = [
    Path(r"C:\Users\shaas\Downloads\finwell_reconciliation_primary_nov2026.pdf"),
    Path(r"C:\Users\shaas\Downloads\finwell_reconciliation_secondary_nov2026.pdf"),
]

for pdf in files:
    print("\n" + "=" * 75)
    print("FILE:", pdf.name)
    print("=" * 75)

    extracted = extract_pdf_text(str(pdf))
    if not extracted.get("success"):
        print("EXTRACTION ERROR:", extracted.get("error"))
        continue

    cleaned = clean_extracted_text(extracted["full_text"])
    if not cleaned.get("success"):
        print("CLEANING ERROR:", cleaned.get("error"))
        continue

    text = cleaned["cleaned_text"]

    print("\n----- CLEANED TEXT -----\n")
    print(text)

    parsed = parse_transactions(text)

    print("\n----- PARSER RESULT -----")
    print("Success:", parsed.get("success"))
    print("Total:", parsed.get("total_transactions"))
    print("Error:", parsed.get("error"))
    print("Transactions:")
    for transaction in parsed.get("transactions", []):
        print(transaction)

