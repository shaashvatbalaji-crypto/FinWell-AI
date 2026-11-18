
import logging
import shutil
import tempfile
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
)

from api.auth_dependencies import get_current_user
from services.ingestion_service import ingest_document


router = APIRouter()

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INCOMING_DIR = PROJECT_ROOT / "data" / "processed" / "incoming"

MAX_FILE_SIZE_MB = 20
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
CHUNK_SIZE = 1024 * 1024


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    account_id: int | None = Form(None),
    user_id: int = Depends(get_current_user),
):
    """
    Upload and process a financial PDF.

    user_id is obtained from the verified JWT.
    account_id remains optional and is validated by ingestion_service.
    """

    temporary_directory = None

    try:
        # 1. Validate authenticated user ID
        if user_id <= 0:
            raise HTTPException(
                status_code=401,
                detail="Invalid authenticated user.",
            )

        # 2. Validate optional account ID
        if account_id is not None and account_id <= 0:
            raise HTTPException(
                status_code=400,
                detail="account_id must be a positive integer.",
            )

        # 3. Validate uploaded filename
        if not file.filename:
            raise HTTPException(
                status_code=400,
                detail="No filename was provided.",
            )

        original_filename = Path(
            file.filename.replace("\\", "/")
        ).name

        if not original_filename:
            raise HTTPException(
                status_code=400,
                detail="Invalid filename.",
            )

        if Path(original_filename).suffix.lower() != ".pdf":
            raise HTTPException(
                status_code=400,
                detail="Only PDF files are supported.",
            )

        # 4. Prepare temporary upload directory
        INCOMING_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary_directory = Path(
            tempfile.mkdtemp(
                prefix="upload_",
                dir=str(INCOMING_DIR),
            )
        )

        temporary_path = temporary_directory / original_filename

        # 5. Save upload in chunks and enforce size limit
        total_size = 0

        with temporary_path.open("wb") as destination:
            while True:
                chunk = await file.read(CHUNK_SIZE)

                if not chunk:
                    break

                total_size += len(chunk)

                if total_size > MAX_FILE_SIZE_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail=(
                            f"File exceeds the "
                            f"{MAX_FILE_SIZE_MB} MB limit."
                        ),
                    )

                destination.write(chunk)

        if total_size == 0:
            raise HTTPException(
                status_code=400,
                detail="The uploaded PDF is empty.",
            )

        # 6. Process the document
        result = ingest_document(
            pdf_path=str(temporary_path),
            user_id=user_id,
            account_id=account_id,
        )

        if not isinstance(result, dict):
            logger.error(
                "Unexpected ingestion result for user_id=%s",
                user_id,
            )

            return {
                "success": False,
                "message": "The ingestion service returned an invalid response.",
            }

        # 7. Handle ingestion failure
        if not result.get("success"):
            return {
                "success": False,
                "stage": result.get("stage"),
                "message": result.get(
                    "message",
                    "Document processing failed.",
                ),
                "document_id": result.get("document_id"),
                "user_id": user_id,
                "account_id": account_id,
                "is_duplicate": result.get("is_duplicate", False),
                "existing_document_id": result.get(
                    "existing_document_id"
                ),
                "parsed_transaction_count": result.get(
                    "parsed_transaction_count", 0
                ),
                "valid_transaction_count": result.get(
                    "valid_transaction_count", 0
                ),
                "invalid_transaction_count": result.get(
                    "invalid_transaction_count", 0
                ),
                "chunk_count": result.get("chunk_count", 0),
            }

        # 8. Map ingestion result fields
        parsed_transactions = result.get(
            "parsed_transaction_count", 0
        )

        valid_transactions = result.get(
            "valid_transaction_count", 0
        )

        invalid_transactions = result.get(
            "invalid_transaction_count", 0
        )

        stored_transactions = result.get(
            "stored_transaction_count", 0
        )

        # 9. Return successful response
        return {
            "success": True,
            "message": result.get(
                "message",
                "Document uploaded and processed successfully.",
            ),
            "document_id": result.get("document_id"),
            "user_id": user_id,
            "account_id": account_id,
            "filename": result.get(
                "filename",
                original_filename,
            ),
            "document_type": result.get("document_type"),
            "page_count": result.get("page_count", 0),
            "character_count": result.get("character_count", 0),
            "chunk_count": result.get("chunk_count", 0),
            "total_transactions": parsed_transactions,
            "parsed_transaction_count": parsed_transactions,
            "valid_transactions": valid_transactions,
            "invalid_transactions": invalid_transactions,
            "stored_transactions": stored_transactions,
            "processing_status": result.get(
                "stage",
                "completed",
            ),
        }

    except HTTPException:
        raise

    except Exception:
        logger.exception(
            "Unexpected upload error for user_id=%s",
            user_id,
        )

        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while uploading the document.",
        )

    finally:
        if temporary_directory is not None:
            shutil.rmtree(
                temporary_directory,
                ignore_errors=True,
            )

        try:
            await file.close()
        except Exception:
            logger.warning("Could not close uploaded file.")
