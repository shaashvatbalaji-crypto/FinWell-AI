import hashlib
import shutil
import uuid
from pathlib import Path

from pdf_extraction.pdf_validator import validate_pdf
from pdf_extraction.pdf_reader import extract_pdf_text
from pdf_extraction.document_classifier import classify_document
from preprocessing.text_cleaner import clean_extracted_text
from preprocessing.transaction_parser import parse_transactions
from preprocessing.data_normalizer import normalize_transactions
from preprocessing.data_validator import validate_transactions

from chroma_pipeline.chunker import chunk_text
from chroma_pipeline.vector_store import add_document_chunks

from mysql_pipeline.document_storage import (
    save_document,
    update_document_status,
    update_document_type,
)

from mysql_pipeline.duplicate_detector import check_duplicate_document

from mysql_pipeline.transaction_storage import (
    save_transactions,
)


# Project root: FinWell_AI/FinWell_AI
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Permanent PDF storage directory
UPLOADS_DIR = PROJECT_ROOT / "data" / "uploads"


def calculate_file_hash(file_path):
    """Calculate the SHA-256 hash of a file."""

    sha256 = hashlib.sha256()

    with open(file_path, "rb") as file:
        for block in iter(lambda: file.read(8192), b""):
            sha256.update(block)

    return sha256.hexdigest()


def create_permanent_copy(source_path, user_id):
    """
    Copy a PDF into the user's permanent upload folder.

    Returns:
        dict: success, stored_filename, stored_path, or error message.
    """

    source_path = Path(source_path)

    try:
        user_upload_dir = UPLOADS_DIR / f"user_{user_id}"
        user_upload_dir.mkdir(parents=True, exist_ok=True)

        # UUID avoids filename collisions and prevents trusting the
        # original filename as a storage path.
        unique_filename = f"{uuid.uuid4().hex}.pdf"
        destination_path = user_upload_dir / unique_filename

        shutil.copy2(source_path, destination_path)

        return {
            "success": True,
            "stored_filename": unique_filename,
            "stored_path": destination_path.resolve(),
        }

    except OSError as error:
        return {
            "success": False,
            "message": f"Could not store uploaded PDF: {error}",
        }


def ingest_document(pdf_path, user_id):
    """
    Ingest a PDF into permanent local storage, MySQL, and ChromaDB.

    Workflow:
        Validate
        -> Hash
        -> Duplicate check
        -> Permanent file copy
        -> MySQL document record
        -> Extract text
        -> Clean text
        -> Classify document
        -> Save document type
        -> Chunk text
        -> Store chunks in ChromaDB
        -> Parse transactions
        -> Normalize transactions
        -> Validate transactions
        -> Store transactions in MySQL
        -> Mark document completed
    """

    source_path = Path(pdf_path)

    # Step 1: Validate the source PDF.
    validation_result = validate_pdf(str(source_path))

    if not validation_result.get("valid"):
        return {
            "success": False,
            "stage": "validation",
            "message": validation_result.get(
                "error",
                "PDF validation failed.",
            ),
        }

    # Step 2: Calculate the file hash.
    file_hash = calculate_file_hash(source_path)

    # Step 3: Check whether this user already uploaded this file.
    duplicate_result = check_duplicate_document(
        user_id=user_id,
        file_hash=file_hash,
    )

    if not duplicate_result.get("success"):
        return {
            "success": False,
            "stage": "duplicate_check",
            "message": duplicate_result.get(
                "message",
                "Duplicate check failed.",
            ),
        }

    if duplicate_result.get("is_duplicate"):
        return {
            "success": False,
            "stage": "duplicate_check",
            "is_duplicate": True,
            "existing_document_id": duplicate_result.get("document_id"),
            "message": "This PDF has already been uploaded by this user.",
        }

    # Step 4: Copy the PDF to permanent storage.
    storage_result = create_permanent_copy(
        source_path=source_path,
        user_id=user_id,
    )

    if not storage_result.get("success"):
        return {
            "success": False,
            "stage": "file_storage",
            "message": storage_result.get(
                "message",
                "Failed to store PDF permanently.",
            ),
        }

    stored_filename = storage_result["stored_filename"]
    stored_path = Path(storage_result["stored_path"])

    # Step 5: Save the permanent file path in MySQL.
    document_result = save_document(
        user_id=user_id,
        original_filename=source_path.name,
        stored_filename=stored_filename,
        file_path=str(stored_path),
        file_hash=file_hash,
        document_type="unknown",
        page_count=validation_result.get("total_pages", 0),
    )

    if not document_result.get("success"):
        # Avoid leaving an untracked file behind if MySQL insert fails.
        try:
            stored_path.unlink(missing_ok=True)
        except OSError:
            pass

        return {
            "success": False,
            "stage": "mysql_document_storage",
            "message": document_result.get(
                "message",
                "Failed to save document record.",
            ),
        }

    document_id = document_result.get("document_id")

    # Step 6: Mark the document as processing.
    status_result = update_document_status(
        document_id=document_id,
        user_id=user_id,
        status="processing",
    )

    if not status_result.get("success"):
        return {
            "success": False,
            "stage": "mysql_status_update",
            "document_id": document_id,
            "message": status_result.get(
                "message",
                "Failed to mark document as processing.",
            ),
        }

    # These values are retained for the final response.
    transaction_count = 0
    valid_transaction_count = 0
    invalid_transaction_count = 0
    chunk_count = 0
    document_type = "unknown"
    cleaned_text = ""

    try:
        # Step 7: Extract text from the permanent stored copy.
        extraction_result = extract_pdf_text(str(stored_path))

        if not extraction_result.get("success"):
            raise RuntimeError(
                extraction_result.get(
                    "error",
                    "PDF text extraction failed.",
                )
            )

        extracted_text = extraction_result.get("full_text", "")

        if not extracted_text.strip():
            raise RuntimeError(
                "No selectable text was found. "
                "OCR is not enabled for scanned PDFs yet."
            )

        # Step 8: Clean extracted text.
        cleaning_result = clean_extracted_text(extracted_text)

        if not cleaning_result.get("success"):
            raise RuntimeError(
                cleaning_result.get(
                    "error",
                    "Text cleaning failed.",
                )
            )

        cleaned_text = cleaning_result.get("cleaned_text", "")

        if not cleaned_text.strip():
            raise RuntimeError("No text remained after cleaning.")

        # Step 9: Classify the document.
        classification_result = classify_document(cleaned_text)

        if not classification_result.get("success"):
            raise RuntimeError(
                classification_result.get(
                    "error",
                    "Document classification failed.",
                )
            )

        document_type = classification_result.get(
            "document_type",
            "unknown",
        )

        # Step 10: Save the detected type in MySQL.
        type_result = update_document_type(
            document_id=document_id,
            user_id=user_id,
            document_type=document_type,
        )

        if not type_result.get("success"):
            raise RuntimeError(
                type_result.get(
                    "message",
                    "Failed to update document type in MySQL.",
                )
            )

        # Step 11: Create text chunks.
        chunks = chunk_text(
            cleaned_text,
            chunk_size=1000,
            chunk_overlap=150,
        )

        if not chunks:
            raise RuntimeError("No text chunks were created.")

        # Step 12: Store chunks in ChromaDB.
        chroma_result = add_document_chunks(
            document_id=document_id,
            user_id=user_id,
            chunks=chunks,
        )

        if not chroma_result.get("success"):
            raise RuntimeError(
                chroma_result.get(
                    "message",
                    "ChromaDB storage failed.",
                )
            )

        chunk_count = chroma_result.get("stored_count", 0)

        # Step 13: Parse transactions from the cleaned text.
        parsing_result = parse_transactions(cleaned_text)

        if not parsing_result.get("success"):
            raise RuntimeError(
                parsing_result.get(
                    "error",
                    "Transaction parsing failed.",
                )
            )

        parsed_transactions = parsing_result.get("transactions", [])
        transaction_count = len(parsed_transactions)

        # Step 14: Normalize parsed transactions.
        normalization_result = normalize_transactions(
            parsed_transactions
        )

        if not normalization_result.get("success"):
            raise RuntimeError(
                normalization_result.get(
                    "error",
                    "Transaction normalization failed.",
                )
            )

        normalized_transactions = normalization_result.get(
            "transactions",
            [],
        )

        # Step 15: Validate normalized transactions.
        validation_result = validate_transactions(
            normalized_transactions
        )

        if not validation_result.get("success"):
            raise RuntimeError(
                validation_result.get(
                    "error",
                    "Transaction validation failed.",
                )
            )

        valid_transactions = validation_result.get(
            "valid_transactions",
            [],
        )

        invalid_transaction_count = validation_result.get(
            "invalid_count",
            0,
        )

        valid_transaction_count = validation_result.get(
            "valid_count",
            len(valid_transactions),
        )

        # Step 16: Save validated transactions to MySQL.
        if valid_transactions:
            transaction_save_result = save_transactions(
                user_id=user_id,
                document_id=document_id,
                transactions=valid_transactions,
            )

            if not transaction_save_result.get("success"):
                raise RuntimeError(
                    transaction_save_result.get(
                        "message",
                        "Failed to save transactions in MySQL.",
                    )
                )

        # Step 17: Mark document as completed.
        status_result = update_document_status(
            document_id=document_id,
            user_id=user_id,
            status="completed",
        )

        if not status_result.get("success"):
            raise RuntimeError(
                status_result.get(
                    "message",
                    "Failed to mark document as completed.",
                )
            )

        # Step 18: Return complete ingestion results.
        return {
            "success": True,
            "stage": "completed",
            "message": "Document ingestion completed successfully.",
            "document_id": document_id,
            "user_id": user_id,
            "filename": source_path.name,
            "stored_filename": stored_filename,
            "file_path": str(stored_path),
            "document_type": document_type,
            "page_count": validation_result.get("total_pages", 0),
            "character_count": len(cleaned_text),
            "chunk_count": chunk_count,
            "parsed_transaction_count": transaction_count,
            "valid_transaction_count": valid_transaction_count,
            "invalid_transaction_count": invalid_transaction_count,
            "stored_transaction_count": len(valid_transactions),
        }

    except Exception as error:
        update_document_status(
            document_id=document_id,
            user_id=user_id,
            status="failed",
            error_message=str(error),
        )

        return {
            "success": False,
            "stage": "processing",
            "document_id": document_id,
            "file_path": str(stored_path),
            "message": str(error),
            "parsed_transaction_count": transaction_count,
            "valid_transaction_count": valid_transaction_count,
            "invalid_transaction_count": invalid_transaction_count,
            "chunk_count": chunk_count,
        }