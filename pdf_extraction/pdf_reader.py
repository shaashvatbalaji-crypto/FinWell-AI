from pathlib import Path
import pymupdf


def extract_pdf_text(pdf_path: str) -> dict:
    """
    Extract text from a PDF, page by page.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        A dictionary containing extracted text and document details.
    """

    path = Path(pdf_path)

    if not path.exists():
        return {
            "success": False,
            "error": "PDF file does not exist."
        }

    try:
        with pymupdf.open(path) as document:

            if document.is_encrypted:
                return {
                    "success": False,
                    "error": "PDF is password-protected."
                }

            pages = []
            full_text = ""

            for page_number, page in enumerate(document, start=1):
                page_text = page.get_text("text")

                pages.append({
                    "page_number": page_number,
                    "text": page_text
                })

                full_text += page_text + "\n"

            return {
                "success": True,
                "filename": path.name,
                "total_pages": document.page_count,
                "full_text": full_text.strip(),
                "pages": pages,
                "error": None
            }

    except Exception:
        return {
            "success": False,
            "error": "Could not read the PDF. It may be corrupted."
        }