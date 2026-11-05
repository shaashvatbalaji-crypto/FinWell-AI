from pathlib import Path
import pdfplumber


def extract_pdf_tables(pdf_path: str) -> dict:
    """
    Extract tables from a PDF using pdfplumber.

    Returns tables grouped by page.
    """

    path = Path(pdf_path)

    if not path.exists():
        return {
            "success": False,
            "error": "PDF file does not exist."
        }

    try:
        extracted_pages = []
        total_tables = 0

        with pdfplumber.open(path) as pdf:

            for page_number, page in enumerate(pdf.pages, start=1):
                tables = page.extract_tables()

                page_tables = []

                for table in tables:
                    if table:
                        page_tables.append(table)
                        total_tables += 1

                extracted_pages.append({
                    "page_number": page_number,
                    "tables": page_tables
                })

        return {
            "success": True,
            "filename": path.name,
            "total_pages": len(extracted_pages),
            "total_tables": total_tables,
            "pages": extracted_pages,
            "error": None
        }

    except Exception:
        return {
            "success": False,
            "error": "Could not extract tables from the PDF."
        }