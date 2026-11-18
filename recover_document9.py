from pathlib import Path

from mysql_pipeline.document_storage import (
    get_document_by_id,
    update_document_status,
    update_document_type,
)
from mysql_pipeline.transaction_storage import save_transactions

from pdf_extraction.pdf_reader import extract_pdf_text
from preprocessing.text_cleaner import clean_extracted_text
from preprocessing.transaction_parser import parse_transactions
from preprocessing.data_normalizer import normalize_transactions
from preprocessing.data_validator import validate_transactions


DOCUMENT_ID = 9
USER_ID = 1


def main():
    # 1. Retrieve the existing document record.
    result = get_document_by_id(
        document_id=DOCUMENT_ID,
        user_id=USER_ID,
    )

    if not result.get("success"):
        raise RuntimeError(result.get("message", "Could not retrieve document."))

    document = result["document"]
    pdf_path = Path(document["file_path"])

    if not pdf_path.exists():
        raise FileNotFoundError(f"Stored PDF not found: {pdf_path}")

    print("Document ID:", DOCUMENT_ID)
    print("Stored PDF:", pdf_path)

    # 2. Mark the existing document as processing.
    status_result = update_document_status(
        document_id=DOCUMENT_ID,
        user_id=USER_ID,
        status="processing",
        error_message=None,
    )

    if not status_result.get("success"):
        raise RuntimeError(status_result.get("message", "Status update failed."))

    try:
        # 3. Extract and clean the PDF text.
        extraction = extract_pdf_text(str(pdf_path))

        if not extraction.get("success"):
            raise RuntimeError(extraction.get("error", "PDF extraction failed."))

        cleaning = clean_extracted_text(extraction.get("full_text", ""))

        if not cleaning.get("success"):
            raise RuntimeError(cleaning.get("error", "Text cleaning failed."))

        cleaned_text = cleaning.get("cleaned_text", "")

        if not cleaned_text.strip():
            raise RuntimeError("No selectable text was extracted.")

        # 4. Parse transactions.
        parsing = parse_transactions(cleaned_text)

        if not parsing.get("success"):
            raise RuntimeError(parsing.get("error", "Transaction parsing failed."))

        parsed = parsing.get("transactions", [])
        print("Parsed transactions:", len(parsed))

        # 5. Normalize transactions.
        normalization = normalize_transactions(parsed)

        if not normalization.get("success"):
            raise RuntimeError(
                normalization.get("error", "Transaction normalization failed.")
            )

        normalized = normalization.get("transactions", [])

        # 6. Validate transactions.
        validation = validate_transactions(normalized)

        if not validation.get("success"):
            raise RuntimeError(
                validation.get("error", "Transaction validation failed.")
            )

        valid = validation.get("valid_transactions", [])
        invalid_count = validation.get("invalid_count", 0)

        print("Valid transactions:", len(valid))
        print("Invalid transactions:", invalid_count)

        # 7. Save transactions under the EXISTING document ID.
        if valid:
            saved = save_transactions(
                user_id=USER_ID,
                document_id=DOCUMENT_ID,
                transactions=valid,
            )

            if not saved.get("success"):
                raise RuntimeError(
                    saved.get("message", "Saving transactions failed.")
                )

        # 8. Mark the existing document completed.
        completed = update_document_status(
            document_id=DOCUMENT_ID,
            user_id=USER_ID,
            status="completed",
            error_message=None,
        )

        if not completed.get("success"):
            raise RuntimeError(
                completed.get("message", "Could not mark document completed.")
            )

        print("\nRECOVERY SUCCESSFUL")
        print("Document ID:", DOCUMENT_ID)
        print("Transactions saved:", len(valid))

    except Exception as error:
        update_document_status(
            document_id=DOCUMENT_ID,
            user_id=USER_ID,
            status="failed",
            error_message=str(error),
        )
        raise


if __name__ == "__main__":
    main()
