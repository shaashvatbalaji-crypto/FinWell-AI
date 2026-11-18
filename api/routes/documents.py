
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Path as ApiPath

from api.auth_dependencies import get_current_user

from mysql_pipeline.document_storage import (
    list_user_documents,
    get_document_by_id,
)

from pdf_extraction.pdf_reader import extract_pdf_text


router = APIRouter()


@router.get("/documents")
def get_user_documents(
    user_id: int = Depends(get_current_user),
):
    """Retrieve documents belonging to the authenticated user."""

    result = list_user_documents(user_id)

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get(
                "message",
                "Could not retrieve documents.",
            ),
        )

    return {
        "success": True,
        "message": result.get("message"),
        "user_id": user_id,
        "count": result.get("count", 0),
        "documents": result.get("documents", []),
    }


@router.get("/documents/{document_id}")
def get_document_details(
    document_id: int = ApiPath(..., gt=0),
    user_id: int = Depends(get_current_user),
):
    """Retrieve metadata for a document belonging to the authenticated user."""

    result = get_document_by_id(
        document_id=document_id,
        user_id=user_id,
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=404,
            detail="Document not found for this user.",
        )

    return {
        "success": True,
        "message": result.get("message"),
        "document": result.get("document"),
    }


@router.get("/documents/{document_id}/text")
def get_document_text(
    document_id: int = ApiPath(..., gt=0),
    user_id: int = Depends(get_current_user),
):
    """Extract text from a PDF belonging to the authenticated user."""

    # 1. Confirm document ownership.
    document_result = get_document_by_id(
        document_id=document_id,
        user_id=user_id,
    )

    if not document_result.get("success"):
        raise HTTPException(
            status_code=404,
            detail="Document not found for this user.",
        )

    document = document_result["document"]

    # 2. Locate the permanently stored PDF.
    pdf_path = Path(document["file_path"])

    if not pdf_path.exists():
        raise HTTPException(
            status_code=404,
            detail="The stored PDF file could not be found.",
        )

    # 3. Extract PDF text.
    extraction_result = extract_pdf_text(str(pdf_path))

    if not extraction_result.get("success"):
        raise HTTPException(
            status_code=422,
            detail=extraction_result.get(
                "error",
                "Could not extract text from this PDF.",
            ),
        )

    full_text = extraction_result.get("full_text", "")
    pages = extraction_result.get("pages", [])

    # 4. Handle scanned PDFs.
    if not full_text.strip():
        raise HTTPException(
            status_code=422,
            detail=(
                "No selectable text was found in this PDF. "
                "OCR is not enabled yet, so scanned PDFs cannot "
                "be processed by this endpoint."
            ),
        )

    # 5. Return extracted text.
    return {
        "success": True,
        "message": "Document text extracted successfully.",
        "document_id": document_id,
        "user_id": user_id,
        "filename": document["original_filename"],
        "document_type": document["document_type"],
        "page_count": extraction_result.get("total_pages", 0),
        "character_count": len(full_text),
        "full_text": full_text,
        "pages": pages,
    }
