
import re

from preprocessing.universal_parser.layout_detector import (
    detect_statement_layout,
)


# Lines that indicate the transaction table has ended.
TABLE_END_MARKERS = [
    "statement summary",
    "summary of transactions",
    "total deposits",
    "total withdrawals",
    "total credits",
    "total debits",
    "closing balance",
    "end of statement",
]


# Lines that should not become transaction records.
# Supports both dated and undated balance-control rows.
NON_TRANSACTION_PATTERNS = [
    r"^\s*page\s+\d+(\s+of\s+\d+)?\s*$",

    r"^\s*(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\s+)?"
    r"balance\s+brought\s+forward\b.*$",

    r"^\s*(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\s+)?"
    r"balance\s+carried\s+forward\b.*$",

    r"^\s*(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\s+)?"
    r"brought\s+forward\b.*$",

    r"^\s*(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\s+)?"
    r"carried\s+forward\b.*$",

    r"^\s*(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\s+)?"
    r"opening\s+balance\b.*$",

    r"^\s*(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\s+)?"
    r"closing\s+balance\b.*$",
]


def _normalize_line(line):
    """Normalize whitespace for comparisons."""

    return " ".join(str(line).split()).strip()


def _is_repeated_header(line):
    """Check whether a line is a repeated transaction header."""

    normalized = _normalize_line(line).lower()

    if not normalized:
        return False

    detected = detect_statement_layout(normalized)

    return (
        detected.get("success")
        and detected.get("recognized")
    )


def _is_non_transaction_line(line):
    """Identify common statement and page-control lines."""

    normalized = _normalize_line(line)

    if not normalized:
        return True

    for pattern in NON_TRANSACTION_PATTERNS:
        if re.match(pattern, normalized, re.IGNORECASE):
            return True

    return False


def _is_table_end(line):
    """Check whether a line indicates the end of transactions."""

    normalized = _normalize_line(line).lower()

    return any(
        normalized.startswith(marker)
        for marker in TABLE_END_MARKERS
    )


def extract_transaction_table(text, layout_result=None):
    """
    Extract the transaction-table section from cleaned statement text.

    Args:
        text: Cleaned statement text.
        layout_result: Optional output from detect_statement_layout().

    Returns:
        Dictionary containing extracted table lines and metadata.

    This module isolates table content. It does not classify
    debit/credit values or construct transaction dictionaries.
    """

    if not isinstance(text, str) or not text.strip():
        return {
            "success": False,
            "recognized": False,
            "header": None,
            "header_line_number": None,
            "transaction_lines": [],
            "total_lines": 0,
            "warnings": [],
            "error": "Input text is empty or invalid.",
        }

    if layout_result is None:
        layout_result = detect_statement_layout(text)

    if not isinstance(layout_result, dict):
        return {
            "success": False,
            "recognized": False,
            "header": None,
            "header_line_number": None,
            "transaction_lines": [],
            "total_lines": 0,
            "warnings": [],
            "error": "Invalid layout detection result.",
        }

    if not layout_result.get("success"):
        return {
            "success": False,
            "recognized": False,
            "header": None,
            "header_line_number": None,
            "transaction_lines": [],
            "total_lines": 0,
            "warnings": [],
            "error": layout_result.get(
                "error",
                "Layout detection failed.",
            ),
        }

    if not layout_result.get("recognized"):
        return {
            "success": True,
            "recognized": False,
            "header": None,
            "header_line_number": None,
            "transaction_lines": [],
            "total_lines": 0,
            "warnings": [
                "Transaction table could not be isolated because "
                "the statement layout was not recognized."
            ],
            "error": None,
        }

    lines = text.splitlines()

    header_line_number = layout_result.get(
        "header_line_number"
    )

    header_line_count = layout_result.get(
        "header_line_count",
        1,
    )

    if (
        not isinstance(header_line_number, int)
        or header_line_number < 1
        or header_line_number > len(lines)
    ):
        return {
            "success": False,
            "recognized": False,
            "header": None,
            "header_line_number": None,
            "transaction_lines": [],
            "total_lines": 0,
            "warnings": [],
            "error": "Detected header line number is invalid.",
        }

    if (
        not isinstance(header_line_count, int)
        or header_line_count < 1
    ):
        return {
            "success": False,
            "recognized": False,
            "header": None,
            "header_line_number": None,
            "transaction_lines": [],
            "total_lines": 0,
            "warnings": [],
            "error": "Detected header line count is invalid.",
        }

    header_start = header_line_number - 1
    header_end = header_start + header_line_count

    if header_end > len(lines):
        return {
            "success": False,
            "recognized": False,
            "header": None,
            "header_line_number": None,
            "transaction_lines": [],
            "total_lines": 0,
            "warnings": [],
            "error": "Detected header extends beyond the input text.",
        }

    header = layout_result.get("header_line")

    transaction_lines = []
    warnings = []

    table_ended = False

    for index in range(header_end, len(lines)):

        original_line = lines[index]
        normalized = _normalize_line(original_line)

        if not normalized:
            continue

        # Stop when the statement enters its summary/footer.
        if _is_table_end(normalized):
            table_ended = True
            break

        # Ignore repeated headers on following pages.
        if _is_repeated_header(normalized):
            continue

        # Ignore page numbers and balance-control rows.
        if _is_non_transaction_line(normalized):
            continue

        # Preserve other nonempty lines, including
        # continuation lines of multiline descriptions.
        transaction_lines.append({
            "line_number": index + 1,
            "text": normalized,
        })

    if not transaction_lines:
        warnings.append(
            "No transaction-table content was found after the header."
        )

    if not table_ended:
        warnings.append(
            "No recognized statement footer was found. "
            "All remaining non-control lines were retained."
        )

    return {
        "success": True,
        "recognized": True,
        "header": header,
        "header_line_number": header_line_number,
        "header_line_count": header_line_count,
        "transaction_lines": transaction_lines,
        "total_lines": len(transaction_lines),
        "table_ended": table_ended,
        "warnings": warnings,
        "error": None,
    }
