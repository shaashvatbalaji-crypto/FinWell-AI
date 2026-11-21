"""FinWell AI — dynamic, read-only PDF ingestion test.

Run from the FinWell_AI project root:
    python .\\run_pdf_ingestion_dynamic_test.py "C:\\path\\to\\statement.pdf"

No account details, statement dates, balances, transaction counts, or expected
amounts are embedded in this test. All values are derived from the supplied PDF
and the existing FinWell extraction/parsing/normalization/validation modules.
No database writes or reconciliation actions are performed.
"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def money(value):
    """Convert a parsed monetary value to cents-safe float; blank means zero."""
    if value is None or value == "":
        return 0.0
    if isinstance(value, (int, float)):
        return round(float(value), 2)
    cleaned = str(value).strip()
    for token in ("₹", "INR", ","):
        cleaned = cleaned.replace(token, "")
    cleaned = cleaned.replace(" ", "")
    if cleaned.startswith("(") and cleaned.endswith(")"):
        cleaned = "-" + cleaned[1:-1]
    return round(float(cleaned), 2)


def first_value(row, *keys):
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return value
    return None


def get_transaction_rows(result, *candidate_keys):
    if isinstance(result, list):
        return result
    if isinstance(result, dict):
        for key in candidate_keys:
            value = result.get(key)
            if isinstance(value, list):
                return value
    raise RuntimeError(
        "Could not locate transaction rows in module response. "
        f"Available response keys: {list(result) if isinstance(result, dict) else type(result).__name__}"
    )


def main():
    if len(sys.argv) != 2:
        print('Usage: python .\\run_pdf_ingestion_dynamic_test.py "<PDF path>"')
        raise SystemExit(64)

    pdf_path = Path(sys.argv[1]).expanduser().resolve()
    require(pdf_path.is_file(), f"PDF not found: {pdf_path}")
    require(pdf_path.suffix.lower() == ".pdf", "Input must be a PDF file")

    # Import only after validating the supplied input path.
    from pdf_extraction.pdf_validator import validate_pdf
    from pdf_extraction.pdf_reader import extract_pdf_text
    from pdf_extraction.document_classifier import classify_document
    from preprocessing.text_cleaner import clean_extracted_text
    from preprocessing.transaction_parser import parse_transactions
    from preprocessing.data_normalizer import normalize_transactions
    from preprocessing.data_validator import validate_transactions

    print("=" * 76)
    print("FINWELL AI — DYNAMIC PDF INGESTION TEST (READ ONLY)")
    print("Input:", pdf_path)
    print("=" * 76)

    print("\n[1] PDF validation")
    pdf_check = validate_pdf(str(pdf_path))
    print(json.dumps(pdf_check, indent=2, default=str))
    require(isinstance(pdf_check, dict) and pdf_check.get("valid") is True,
            "PDF validation did not return valid=True")

    print("\n[2] Text extraction")
    extracted = extract_pdf_text(str(pdf_path))
    require(isinstance(extracted, dict) and extracted.get("success") is True,
            f"Text extraction failed: {extracted}")
    raw_text = extracted.get("full_text", "")
    require(isinstance(raw_text, str) and raw_text.strip(),
            "No selectable text was extracted. OCR may be required for this PDF.")
    print("Pages:", extracted.get("total_pages", "not reported"))
    print("Extracted characters:", len(raw_text))

    print("\n[3] Text cleaning")
    cleaned_result = clean_extracted_text(raw_text)
    require(isinstance(cleaned_result, dict) and cleaned_result.get("success") is True,
            f"Text cleaning failed: {cleaned_result}")
    cleaned_text = cleaned_result.get("cleaned_text", "")
    require(isinstance(cleaned_text, str) and cleaned_text.strip(),
            "Cleaner returned empty text")
    print("Cleaned characters:", len(cleaned_text))

    print("\n[4] Dynamic document classification")
    classification = classify_document(cleaned_text)
    print(json.dumps(classification, indent=2, default=str))
    require(isinstance(classification, dict) and classification.get("success") is True,
            f"Document classification failed: {classification}")
    print("Predicted document type:", classification.get("document_type", "not reported"))

    print("\n[5] Transaction parsing")
    parsed_result = parse_transactions(cleaned_text)
    require(isinstance(parsed_result, dict) and parsed_result.get("success") is True,
            f"Transaction parsing failed: {parsed_result}")
    parsed_rows = get_transaction_rows(parsed_result, "transactions", "parsed_transactions", "data")
    print("Transactions predicted by parser:", len(parsed_rows))

    print("\n[6] Normalization")
    normalized_result = normalize_transactions(parsed_rows)
    if isinstance(normalized_result, dict):
        require(normalized_result.get("success") is True,
                f"Normalization failed: {normalized_result}")
    normalized_rows = get_transaction_rows(
        normalized_result, "transactions", "normalized_transactions", "data"
    )
    print("Normalized transactions:", len(normalized_rows))

    print("\n[7] Transaction validation")
    validation_result = validate_transactions(normalized_rows)
    require(isinstance(validation_result, dict) and validation_result.get("success") is True,
            f"Transaction validation failed: {validation_result}")
    valid_rows = get_transaction_rows(
        validation_result, "valid_transactions", "transactions", "valid", "data"
    )
    invalid_rows = validation_result.get("invalid_transactions", [])
    if not isinstance(invalid_rows, list):
        invalid_rows = []
    print("Valid rows:", len(valid_rows))
    print("Invalid rows:", len(invalid_rows))

    print("\n[8] PDF-derived transaction output")
    total_debits = 0.0
    total_credits = 0.0
    for index, row in enumerate(valid_rows, 1):
        require(isinstance(row, dict), f"Transaction {index} is not a dictionary: {row!r}")
        debit = money(first_value(row, "debit", "withdrawal", "debit_amount"))
        credit = money(first_value(row, "credit", "deposit", "credit_amount"))
        total_debits = round(total_debits + debit, 2)
        total_credits = round(total_credits + credit, 2)
        print(
            f"{index:03d} | Date={first_value(row, 'date', 'transaction_date')} | "
            f"Description={first_value(row, 'description', 'narration', 'details')} | "
            f"Debit={debit:.2f} | Credit={credit:.2f} | "
            f"Balance={first_value(row, 'balance', 'running_balance')}"
        )

    print("\n[9] Totals derived from predicted transactions")
    print(f"Predicted debit total:  INR {total_debits:,.2f}")
    print(f"Predicted credit total: INR {total_credits:,.2f}")
    print(f"Net movement:           INR {total_credits - total_debits:,.2f}")
    print("These are parser-derived totals, not hardcoded expected values.")
    print("Statement summary/balance comparison must be supplied by the app's own extracted fields if available.")

    print("\n[10] Side-effect check")
    print("MySQL writes: 0 (not invoked by this runner)")
    print("ChromaDB writes: 0 (not invoked by this runner)")
    print("Reconciliation actions: none")

    if invalid_rows:
        print("\nRESULT: PIPELINE EXECUTED; INVALID TRANSACTIONS REQUIRE REVIEW.")
        print(json.dumps(invalid_rows, indent=2, default=str))
        raise SystemExit(2)
    if not valid_rows:
        print("\nRESULT: NO VALID TRANSACTIONS WERE RETURNED.")
        raise SystemExit(2)

    print("\nRESULT: DYNAMIC PDF INGESTION PIPELINE COMPLETED.")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:
        print(f"\nTEST STOPPED: {type(exc).__name__}: {exc}")
        raise SystemExit(1)
