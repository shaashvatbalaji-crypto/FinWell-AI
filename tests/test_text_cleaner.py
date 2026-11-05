from preprocessing.text_cleaner import clean_extracted_text


def test_clean_whitespace():
    messy_text = "  Date     Description   Amount  \n  01-11-2026   Grocery Store   250  "

    result = clean_extracted_text(messy_text)

    assert result["success"] is True
    assert result["cleaned_text"] == (
        "Date Description Amount\n"
        "01-11-2026 Grocery Store 250"
    )

    print("PASS: Whitespace cleaned")


def test_preserve_line_breaks():
    text = "Transaction 1\nTransaction 2\nTransaction 3"

    result = clean_extracted_text(text)

    assert result["success"] is True
    assert result["cleaned_text"].count("\n") == 2

    print("PASS: Line breaks preserved")


def test_remove_excessive_blank_lines():
    text = "Header\n\n\n\nTransaction"

    result = clean_extracted_text(text)

    assert result["success"] is True
    assert result["cleaned_text"] == "Header\n\nTransaction"

    print("PASS: Excessive blank lines removed")


def test_normalize_line_endings():
    text = "Line 1\r\nLine 2\rLine 3"

    result = clean_extracted_text(text)

    assert result["success"] is True
    assert result["cleaned_text"] == "Line 1\nLine 2\nLine 3"

    print("PASS: Line endings normalized")


def test_empty_input():
    result = clean_extracted_text("")

    assert result["success"] is False
    assert result["error"] == "Input text is empty."

    print("PASS: Empty input handled")


def test_non_string_input():
    result = clean_extracted_text(None)

    assert result["success"] is False
    assert result["error"] == "Input must be a string."

    print("PASS: Non-string input handled")


if __name__ == "__main__":
    test_clean_whitespace()
    test_preserve_line_breaks()
    test_remove_excessive_blank_lines()
    test_normalize_line_endings()
    test_empty_input()
    test_non_string_input()

    print("\nAll text cleaner tests passed!")