from pathlib import Path
import pymupdf

from pdf_extraction.table_extractor import extract_pdf_tables


# Create a sample PDF with a bordered table
sample_path = Path("tests/sample_table.pdf")

with pymupdf.open() as document:
    page = document.new_page()

    rows = [
        ["Date", "Description", "Debit", "Credit"],
        ["01-11-2026", "Grocery Store", "850.00", ""],
        ["02-11-2026", "Monthly Salary", "", "25000.00"],
        ["03-11-2026", "Electricity Bill", "1200.00", ""],
    ]

    # Table layout
    x0, y0 = 40, 60
    col_widths = [100, 180, 100, 100]
    row_height = 30

    # Draw horizontal lines
    table_width = sum(col_widths)

    for row_index in range(len(rows) + 1):
        y = y0 + row_index * row_height
        page.draw_line(
            (x0, y),
            (x0 + table_width, y),
            color=(0, 0, 0),
            width=1
        )

    # Draw vertical lines
    x = x0
    page.draw_line(
        (x, y0),
        (x, y0 + len(rows) * row_height),
        color=(0, 0, 0),
        width=1
    )

    for width in col_widths:
        x += width
        page.draw_line(
            (x, y0),
            (x, y0 + len(rows) * row_height),
            color=(0, 0, 0),
            width=1
        )

    # Insert cell text
    x_positions = [x0 + 5]

    for width in col_widths[:-1]:
        x_positions.append(x_positions[-1] + width)

    for row_index, row in enumerate(rows):
        for column_index, cell in enumerate(row):
            page.insert_text(
                (
                    x_positions[column_index],
                    y0 + row_index * row_height + 20
                ),
                cell,
                fontsize=9
            )

    document.save(sample_path)


# Test 1: Extract bordered table
result = extract_pdf_tables(str(sample_path))

print("TEST 1: Bordered table extraction")
print(result)

assert result["success"] is True
assert result["total_pages"] == 1
assert result["total_tables"] >= 1

# Confirm that extracted table contains expected content
extracted_text = str(result["pages"])

assert "Grocery Store" in extracted_text
assert "Monthly Salary" in extracted_text

print("\nTEST 1 passed!")


# Test 2: Missing PDF
result = extract_pdf_tables("tests/missing_table.pdf")

print("\nTEST 2: Missing PDF")
print(result)

assert result["success"] is False

print("\nAll table extractor tests passed!")