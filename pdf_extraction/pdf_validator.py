
from pathlib import Path
import pymupdf


# Maximum allowed PDF size: 20 MB
MAX_FILE_SIZE = 20 * 1024 * 1024

# PDF file signature
PDF_SIGNATURE = b"%PDF-"


def validate_pdf(pdf_path: str) -> dict:
    """
    Validate a PDF file before extraction.

    Returns:
        Dictionary containing validation status and metadata.
    """

    path = Path(pdf_path)

    # Step 1: Check whether file exists
    if not path.exists():

        return {
            "valid": False,
            "error": "File does not exist."
        }

    # Step 2: Check file extension
    if path.suffix.lower() != ".pdf":

        return {
            "valid": False,
            "error": "Only PDF files are supported."
        }

    # Step 3: Check file size
    file_size = path.stat().st_size

    if file_size == 0:

        return {
            "valid": False,
            "error": "The uploaded file is empty."
        }

    if file_size > MAX_FILE_SIZE:

        return {
            "valid": False,
            "error": "PDF exceeds the 20 MB size limit."
        }

    # Step 4: Check PDF signature
    with open(path, "rb") as file:

        signature = file.read(5)

    if signature != PDF_SIGNATURE:

        return {
            "valid": False,
            "error": "Invalid PDF file signature."
        }

    # Step 5: Check PDF integrity
    try:

        with pymupdf.open(path) as document:

            # Check page count
            if document.page_count == 0:

                return {
                    "valid": False,
                    "error": "PDF contains no pages."
                }

            # Step 6: Return validation metadata
            return {
                "valid": True,
                "filename": path.name,
                "file_size_bytes": file_size,
                "total_pages": document.page_count,
                "encrypted": document.is_encrypted,
                "error": None
            }

    except Exception:

        return {
            "valid": False,
            "error": "PDF is corrupted or cannot be opened."
        }
