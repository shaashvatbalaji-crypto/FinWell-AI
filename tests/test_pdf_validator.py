
from pathlib import Path
import pymupdf

from pdf_extraction.pdf_validator import validate_pdf


# Create a valid sample PDF
sample_path = Path("tests/sample.pdf")

with pymupdf.open() as document:

    page = document.new_page()

    page.insert_text(
        (72, 72),
        "FinWell AI PDF Validation Test"
    )

    document.save(sample_path)


# Test 1: Valid PDF
result = validate_pdf(str(sample_path))

print("TEST 1: Valid PDF")
print(result)

assert result["valid"] is True


# Test 2: Missing file
result = validate_pdf("missing.pdf")

print("\nTEST 2: Missing PDF")
print(result)

assert result["valid"] is False


# Test 3: Invalid PDF
invalid_path = Path("tests/invalid.pdf")

invalid_path.write_bytes(b"This is not a PDF")

result = validate_pdf(str(invalid_path))

print("\nTEST 3: Invalid PDF")
print(result)

assert result["valid"] is False


print("\nAll PDF validation tests passed!")
