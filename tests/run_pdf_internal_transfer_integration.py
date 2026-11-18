import json
import re
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from pdf_extraction.pdf_validator import validate_pdf
from pdf_extraction.pdf_reader import extract_pdf_text
from pdf_extraction.document_classifier import classify_document

from preprocessing.text_cleaner import clean_extracted_text
from preprocessing.transaction_parser import parse_transactions
from preprocessing.data_normalizer import normalize_transactions
from preprocessing.data_validator import validate_transactions

from reconciliation.internal_transfer_matcher import reconcile_internal_transfers


PRIMARY_PDF = Path(
    r"C:\Users\shaas\Downloads\finwell_reconciliation_primary_nov2026.pdf"
)

SECONDARY_PDF = Path(
    r"C:\Users\shaas\Downloads\finwell_reconciliation_secondary_nov2026.pdf"
)

TEST_USER_ID = 9001
PRIMARY_ACCOUNT_ID = 9101
SECONDARY_ACCOUNT_ID = 9102


def process_pdf(pdf_path, account_id, expected_suffix):
    print(f"\n{'=' * 65}")
    print(f"PROCESSING: {pdf_path.name}")
    print("=" * 65)

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    # 1. PDF validation
    pdf_check = validate_pdf(str(pdf_path))
    print("\nPDF validation:", pdf_check)

    if not pdf_check.get("valid"):
        raise RuntimeError(f"PDF validation failed: {pdf_path.name}")

    # 2. Extract text
    extraction = extract_pdf_text(str(pdf_path))

    if not extraction.get("success"):
        raise RuntimeError(extraction.get("error", "PDF extraction failed"))

    extracted_text = extraction.get("full_text", "")

    if not extracted_text.strip():
        raise RuntimeError("PDF contains no selectable text")

    # 3. Use the same cleaner as the existing ingestion service
    cleaning = clean_extracted_text(extracted_text)

    if not cleaning.get("success"):
        raise RuntimeError(cleaning.get("error", "Text cleaning failed"))

    cleaned_text = cleaning.get("cleaned_text", "")

    # 4. Verify statement identity before treating account metadata as verified
    digits = re.sub(r"\D", "", extracted_text)

    if expected_suffix not in digits:
        raise RuntimeError(
            f"Expected account suffix {expected_suffix} was not found "
            f"in {pdf_path.name}"
        )

    if "ARJUN KUMAR" not in extracted_text.upper():
        raise RuntimeError(
            f"Expected account holder Arjun Kumar was not found "
            f"in {pdf_path.name}"
        )

    # 5. Classify document, as in the existing ingestion flow
    classification = classify_document(cleaned_text)

    if not classification.get("success"):
        raise RuntimeError(
            classification.get("error", "Document classification failed")
        )

    # 6. Parse transactions
    parsing = parse_transactions(cleaned_text)

    if not parsing.get("success"):
        raise RuntimeError(parsing.get("error", "Transaction parsing failed"))

    parsed = parsing.get("transactions", [])

    # 7. Normalize
    normalization = normalize_transactions(parsed)

    if not normalization.get("success"):
        raise RuntimeError(
            normalization.get("error", "Transaction normalization failed")
        )

    normalized = normalization.get("transactions", [])

    # 8. Validate
    validation = validate_transactions(normalized)

    if not validation.get("success"):
        raise RuntimeError(
            validation.get("error", "Transaction validation failed")
        )

    valid = validation.get("valid_transactions", [])
    invalid = validation.get("invalid_transactions", [])

    print("\nDocument type:", classification.get("document_type"))
    print("Pages:", extraction.get("total_pages"))
    print("Parsed transactions:", len(parsed))
    print("Valid transactions:", len(valid))
    print("Invalid transactions:", validation.get("invalid_count", len(invalid)))

    if invalid:
        print("\nInvalid transaction records:")
        print(json.dumps(invalid, indent=2, default=str))
        raise RuntimeError(
            "Invalid rows found. Stopping reconciliation rather than "
            "silently excluding transactions."
        )

    # Add temporary in-memory identity fields.
    # These IDs do not exist in MySQL.
    enriched = []

    for transaction in valid:
        item = dict(transaction)

        item["transaction_id"] = None
        item["user_id"] = TEST_USER_ID
        item["account_id"] = account_id
        item["currency"] = "INR"

        # Matcher expects the field name 'date'.
        if not item.get("date"):
            item["date"] = item.get("transaction_date")

        if not item.get("date"):
            raise RuntimeError(
                f"Transaction has no usable date: {transaction}"
            )

        enriched.append(item)

    return {
        "transactions": enriched,
        "account_id": account_id,
        "filename": pdf_path.name,
    }


def main():
    primary = process_pdf(
        PRIMARY_PDF,
        PRIMARY_ACCOUNT_ID,
        "4821",
    )

    secondary = process_pdf(
        SECONDARY_PDF,
        SECONDARY_ACCOUNT_ID,
        "7392",
    )

    accounts = {
        PRIMARY_ACCOUNT_ID: {
            "account_id": PRIMARY_ACCOUNT_ID,
            "user_id": TEST_USER_ID,
            "verified": True,
            "masked_account_number": "XXXX XXXX 4821",
        },
        SECONDARY_ACCOUNT_ID: {
            "account_id": SECONDARY_ACCOUNT_ID,
            "user_id": TEST_USER_ID,
            "verified": True,
            "masked_account_number": "XXXX XXXX 7392",
        },
    }

    all_transactions = []
    next_id = 100001

    for statement in (primary, secondary):
        for transaction in statement["transactions"]:
            transaction["transaction_id"] = next_id
            all_transactions.append(transaction)
            next_id += 1

    print(f"\n{'=' * 65}")
    print("RUNNING INTERNAL TRANSFER RECONCILIATION")
    print("=" * 65)

    result = reconcile_internal_transfers(
        all_transactions,
        accounts,
        max_date_gap_days=1,
    )

    print("\nRECONCILIATION RESULT")
    print(json.dumps(result, indent=2, default=str))

    print("\nSAFETY CHECK")
    print("Mode:", result.get("mode"))
    print("Writes performed:", result.get("writes_performed"))
    print("Transactions tested:", len(all_transactions))

    if result.get("writes_performed") is not False:
        raise RuntimeError("Unexpected write activity reported by matcher")

    print("\nPDF INTERNAL TRANSFER TEST FINISHED.")


if __name__ == "__main__":
    main()

