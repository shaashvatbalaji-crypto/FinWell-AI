
import re


def clean_extracted_text(text: str) -> dict:
    """
    Clean extracted PDF statement text while preserving meaningful
    transaction descriptions and multiline transaction information.

    Removes:
    - Synthetic test-data notices
    - Bank statement headers and taglines
    - Repeated page headers and footers
    - Page numbers
    - Repeated transaction table headings
    - Statement footer content beginning with END OF STATEMENT
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

        # 1. Normalize line endings.
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # 2. Normalize non-breaking spaces.
        text = text.replace("\u00A0", " ")

        # 3. Remove unwanted control characters.
        text = "".join(
            character
            for character in text
            if character in ("\n", "\t") or ord(character) >= 32
        )

        cleaned_lines = []

        # 4. Process extracted lines.
        for line in text.split("\n"):

            line = re.sub(r"[ \t]+", " ", line).strip()

            if not line:
                cleaned_lines.append("")
                continue

            # Stop at the statement footer.
            if re.search(
                r"\bEND OF STATEMENT\b",
                line,
                flags=re.IGNORECASE
            ):
                break

            # Remove synthetic statement notices.
            if re.match(
                r"^(?:.*?\s+-\s+)?"
                r"(?:synthetic test data|computer generated statement)",
                line,
                flags=re.IGNORECASE
            ):
                continue

            # Preserve support for the previously tested Meridian Crest format.
            if re.match(
                r"^Meridian Crest Bank\s*\|\s*Statement for A/c\b",
                line,
                flags=re.IGNORECASE
            ):
                continue

            # Remove standalone statement titles.
            if re.fullmatch(
                r"STATEMENT OF ACCOUNT",
                line,
                flags=re.IGNORECASE
            ):
                continue

            # Remove standalone bank names in uppercase.
            # This avoids removing transaction descriptions containing bank names.
            if (
                line.isupper()
                and re.fullmatch(
                    r"[A-Z0-9&.' -]{2,60}\bBANK",
                    line
                )
            ):
                continue

            # Remove generic banking taglines.
            if re.fullmatch(
                r"Trusted banking, every step of the way",
                line,
                flags=re.IGNORECASE
            ):
                continue

            # Remove page labels.
            if re.fullmatch(
                r"Page\s+\d+(?:\s+of\s+\d+)?",
                line,
                flags=re.IGNORECASE
            ):
                continue

            # Remove repeated table headings.
            normalized_line = re.sub(
                r"\s+",
                " ",
                line
            ).strip().lower()

            table_headers = {
                "date",
                "description",
                "debit",
                "credit",
                "balance",
                "debit (inr)",
                "credit (inr)",
                "balance (inr)",
                "debit (₹)",
                "credit (₹)",
                "balance (₹)",
                "value date",
                "cheque",
                "cheque no"
            }

            if normalized_line in table_headers:
                continue

            cleaned_lines.append(line)

        # 5. Reconstruct cleaned text.
        cleaned_text = "\n".join(cleaned_lines)

        # 6. Allow at most one blank line between content.
        cleaned_text = re.sub(
            r"\n{3,}",
            "\n\n",
            cleaned_text
        )

        # 7. Remove leading and trailing blank lines.
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
            "original_char_count": original_char_count,
            "cleaned_char_count": 0,
            "error": str(error)
        }
