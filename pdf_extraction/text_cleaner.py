import re


def clean_extracted_text(text: str) -> dict:
    """
    Clean extracted PDF text while preserving meaningful line breaks.

    Returns:
        success
        cleaned_text
        original_char_count
        cleaned_char_count
        error
    """

    if not isinstance(text, str):
        return {
            "success": False,
            "cleaned_text": "",
            "original_char_count": 0,
            "cleaned_char_count": 0,
            "error": "Input must be a string."
        }

    if not text.strip():
        return {
            "success": False,
            "cleaned_text": "",
            "original_char_count": len(text),
            "cleaned_char_count": 0,
            "error": "Input text is empty."
        }

    try:
        original_char_count = len(text)

        # Normalize Windows and old-style line endings
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # Replace non-breaking spaces with normal spaces
        text = text.replace("\u00A0", " ")

        # Remove null characters and unwanted control characters
        text = "".join(
            character
            for character in text
            if character == "\n" or character == "\t" or ord(character) >= 32
        )

        cleaned_lines = []

        for line in text.split("\n"):
            # Replace tabs and repeated spaces with one space
            line = re.sub(r"[ \t]+", " ", line)

            # Remove spaces at the beginning and end of each line
            line = line.strip()

            cleaned_lines.append(line)

        # Rebuild text while preserving line structure
        cleaned_text = "\n".join(cleaned_lines)

        # Keep at most one blank line between content
        cleaned_text = re.sub(r"\n{3,}", "\n\n", cleaned_text)

        # Remove blank lines at the beginning and end
        cleaned_text = cleaned_text.strip()

        return {
            "success": True,
            "cleaned_text": cleaned_text,
            "original_char_count": original_char_count,
            "cleaned_char_count": len(cleaned_text),
            "error": None
        }

    except Exception as error:
        return {
            "success": False,
            "cleaned_text": "",
            "original_char_count": len(text),
            "cleaned_char_count": 0,
            "error": str(error)
        }