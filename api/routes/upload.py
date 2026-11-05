
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from services.ingestion_service import ingest_document


router = APIRouter()

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEMP_UPLOAD_DIR = PROJECT_ROOT / "data" / "processed" / "incoming"

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB


@router.post("/upload")
async def upload_financial_document(
    user_id: int = Form(...),
    file: UploadFile = File(...),
):
    """
    Upload and process a financial PDF.

    Pipeline:
    PDF upload -> validation -> extraction -> classification
    -> chunking -> transaction parsing -> validation
    -> MySQL storage -> ChromaDB storage
    """

    # 1. Validate user ID
    if user_id <= 0:
        raise HTTPException(
            status_code=400,
            detail="user_id must be a positive integer.",
        )

    # 2. Validate filename
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No filename was provided.",
        )

    # 3. Accept only PDF files
    if Path(file.filename).suffix.lower() != ".pdf":
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are accepted.",
        )

    TEMP_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    temporary_path = TEMP_UPLOAD_DIR / f"{uuid.uuid4().hex}.pdf"
    file_size = 0

    try:
        # 4. Save upload in chunks and enforce the 20 MB limit
        with temporary_path.open("wb") as destination:
            while True:
                chunk = await file.read(1024 * 1024)

                if not chunk:
                    break

                file_size += len(chunk)

                if file_size > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail="PDF exceeds the maximum allowed size of 20 MB.",
                    )

                destination.write(chunk)

        # 5. Reject empty uploads
        if file_size == 0:
            raise HTTPException(
                status_code=400,
                detail="The uploaded file is empty.",
            )

        # 6. Run the ingestion pipeline
        result = ingest_document(
            pdf_path=str(temporary_path),
            user_id=user_id,
        )

        # 7. Handle duplicate documents
        if (
            not result.get("success")
            and (
                result.get("is_duplicate")
                or result.get("stage") in {
                    "duplicate",
                    "duplicate_check",
                }
            )
        ):
            raise HTTPException(
                status_code=409,
                detail=result.get(
                    "message",
                    "This document has already been uploaded.",
                ),
            )

        # 8. Handle other ingestion failures
        if not result.get("success"):
            raise HTTPException(
                status_code=422,
                detail=result.get(
                    "message",
                    "The document could not be processed.",
                ),
            )

        # 9. Read transaction counts from the ingestion result.
        # The ingestion service currently returns
        # "stored_transaction_count", not "saved_transaction_count".
        parsed_count = result.get(
            "parsed_transaction_count",
            result.get("total_transactions", 0),
        )

        valid_count = result.get(
            "valid_transaction_count",
            result.get("valid_count", 0),
        )

        invalid_count = result.get(
            "invalid_transaction_count",
            result.get("invalid_count", 0),
        )

        saved_count = result.get(
            "stored_transaction_count",
            result.get(
                "saved_transaction_count",
                result.get("saved_count", 0),
            ),
        )

        # 10. Return successful response
        return {
            "success": True,
            "message": "Financial document uploaded and processed successfully.",
            "document": {
                "document_id": result.get("document_id"),
                "user_id": result.get("user_id"),
                "filename": result.get("filename"),
                "document_type": result.get("document_type"),
                "page_count": result.get("page_count"),
                "character_count": result.get("character_count"),
                "chunk_count": result.get("chunk_count"),
                "processing_status": result.get("stage"),
            },
            "transactions": {
                "parsed_count": parsed_count,
                "valid_count": valid_count,
                "invalid_count": invalid_count,
                "saved_count": saved_count,
            },
        }

    except HTTPException:
        # Preserve intended HTTP errors such as 400, 409, 413, and 422.
        raise

    except Exception as error:
        # Unexpected server-side error
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected upload error: {str(error)}",
        )

    finally:
        # 11. Remove temporary upload file
        if temporary_path.exists():
            temporary_path.unlink()

        # 12. Close uploaded file
        await file.close()
