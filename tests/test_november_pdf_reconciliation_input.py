
"""
FinWell AI - November PDF Reconciliation Input Test

Runs the actual PDF preprocessing pipeline on both test statements.

Read-only:
- No MySQL writes
- No ChromaDB writes
- No reconciliation case creation
- No transaction storage
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pdf_extraction.pdf_validator import validate_pdf
from pdf_extraction.pdf_reader import extract_pdf_text
from preprocessing.text_cleaner import clean_extracted_text
from preprocessing.transaction_parser import parse_transactions
from preprocessing.data_normalizer import normalize_transactions
from preprocessing.data_validator import validate_transactions


PDF_FILES = {
    "primary": Path(
        r"C:\Users\shaas\Downloads\finwell_reconciliation_primary_nov2026.pdf"
    ),
    "secondary": Path(
        r"C:\Users\shaas\Downloads\finwell_reconciliation_secondary_nov2026.pdf"
    ),
}


def get_cleaned_text(cleaning_result):
    """Extract cleaned text from the existing cleaner response."""

    if isinstance(cleaning_result, str):
        return cleaning_result

    if isinstance(cleaning_result, dict):
        possible_keys = [
            "cleaned_text",
            "clean_text",
            "text",
            "content",
            "full_text",
            "extracted_text",
        ]

        for key in possible_keys:
            value = cleaning_result.get(key)

            if isinstance(value, str):
                return value

    raise ValueError(
        "Could not identify cleaned text in cleaner response."
    )


def process_pdf(label, pdf_path):
    print("\n" + "=" * 65)
    print(f"PROCESSING: {label.upper()}")
    print("=" * 65)

    if not pdf_path.exists():
        raise FileNotFoundError(str(pdf_path))

    # STEP 1: PDF validation
    validation = validate_pdf(str(pdf_path))

    print("\n[1] PDF VALIDATION")
    print(validation)

    if not validation.get("valid"):
        raise RuntimeError(
            f"PDF validation failed: {validation.get('error')}"
        )

    # STEP 2: Extract text
    extraction = extract_pdf_text(str(pdf_path))

    print("\n[2] PDF EXTRACTION")

    if not extraction.get("success"):
        raise RuntimeError(
            f"PDF extraction failed: {extraction.get('error')}"
        )

    extracted_text = extraction.get("full_text", "")

    print("Pages:", extraction.get("total_pages"))
    print("Extracted characters:", len(extracted_text))

    # STEP 3: Clean text using the actual ingestion cleaner
    cleaning_result = clean_extracted_text(extracted_text)
    cleaned_text = get_cleaned_text(cleaning_result)

    print("\n[3] TEXT CLEANING")
    print("Cleaned characters:", len(cleaned_text))

    # STEP 4: Parse transactions
    parsing_result = parse_transactions(cleaned_text)

    if not parsing_result.get("success"):
        raise RuntimeError(
            f"Transaction parsing failed: "
            f"{parsing_result.get('error')}"
        )

    parsed_transactions = parsing_result.get(
        "transactions", []
    )

    print("\n[4] TRANSACTION PARSING")
    print("Parsed transactions:", len(parsed_transactions))

    # STEP 5: Normalize
    normalization_result = normalize_transactions(
        parsed_transactions
    )

    if not normalization_result.get("success"):
        raise RuntimeError(
            f"Normalization failed: "
            f"{normalization_result.get('error')}"
        )

    normalized_transactions = normalization_result.get(
        "transactions", []
    )

    print("\n[5] NORMALIZATION")
    print(
        "Normalized transactions:",
        len(normalized_transactions),
    )

    # STEP 6: Validate
    validation_result = validate_transactions(
        normalized_transactions
    )

    if not validation_result.get("success"):
        raise RuntimeError(
            "Transaction validation failed: "
            + str(validation_result.get("message"))
        )

    valid_transactions = validation_result.get(
        "valid_transactions", []
    )

    invalid_count = validation_result.get(
        "invalid_count", 0
    )

    print("\n[6] TRANSACTION VALIDATION")
    print("Valid transactions:", len(valid_transactions))
    print("Invalid transactions:", invalid_count)

    # Calculate totals from validated transactions.
    total_debit = sum(
        float(transaction.get("debit") or 0)
        for transaction in valid_transactions
    )

    total_credit = sum(
        float(transaction.get("credit") or 0)
        for transaction in valid_transactions
    )

    print("\n[7] VALIDATED FINANCIAL TOTALS")
    print(f"Total debit:  INR {total_debit:,.2f}")
    print(f"Total credit: INR {total_credit:,.2f}")

    print("\n[8] VALIDATED TRANSACTION DETAILS")

    for index, transaction in enumerate(
        valid_transactions,
        start=1,
    ):
        print(
            f"{index:02d}. "
            f"Date={transaction.get('date')} | "
            f"Description={transaction.get('description')} | "
            f"Debit={transaction.get('debit')} | "
            f"Credit={transaction.get('credit')} | "
            f"Balance={transaction.get('balance')}"
        )

    return {
        "label": label,
        "pdf_path": str(pdf_path),
        "parsed_count": len(parsed_transactions),
        "valid_count": len(valid_transactions),
        "invalid_count": invalid_count,
        "total_debit": round(total_debit, 2),
        "total_credit": round(total_credit, 2),
        "transactions": valid_transactions,
    }


def main():
    results = {}

    for label, pdf_path in PDF_FILES.items():
        results[label] = process_pdf(label, pdf_path)

    print("\n" + "=" * 65)
    print("FINAL NOVEMBER PDF PREPROCESSING SUMMARY")
    print("=" * 65)

    for label, result in results.items():
        print(f"\n{label.upper()}")
        print("Parsed:", result["parsed_count"])
        print("Valid:", result["valid_count"])
        print("Invalid:", result["invalid_count"])
        print(f"Debit: INR {result['total_debit']:,.2f}")
        print(f"Credit: INR {result['total_credit']:,.2f}")

    print("\nNo database or vector-store writes were performed.")
    print("PDF preprocessing test completed.")


if __name__ == "__main__":
    main()
