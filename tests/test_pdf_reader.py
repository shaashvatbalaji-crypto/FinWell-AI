from pathlib import Path
import pymupdf

from pdf_extraction.pdf_reader import extract_pdf_text


# Create a sample PDF with text
sample_path = Path("tests/sample_reader.pdf")

with pymupdf.open() as document:
    page1 = document.new_page()
    page1.insert_text((72, 72), "FinWell AI PDF Reader Test")
    page1.insert_text((72, 100), "Account: 123456789")
    page1.insert_text((72, 128), "Balance: 25000.00")

    page2 = document.new_page()
    page2.insert_text((72, 72), "Second page of the test document")

    document.save(sample_path)


# Test 1: Extract text from valid PDF
result = extract_pdf_text(str(sample_path))

print("TEST 1: Valid PDF text extraction")
print("Success:", result["success"])
print("Pages:", result["total_pages"])
print("Extracted text:")
print(result["full_text"])

assert result["success"] is True
assert result["total_pages"] == 2
assert "FinWell AI PDF Reader Test" in result["full_text"]
assert "Balance: 25000.00" in result["full_text"]


# Test 2: Missing PDF
result = extract_pdf_text("tests/missing_reader.pdf")

print("\nTEST 2: Missing PDF")
print(result)

assert result["success"] is False


print("\nAll PDF reader tests passed!")