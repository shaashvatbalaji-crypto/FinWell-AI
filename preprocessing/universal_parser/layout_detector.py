
import re


COLUMN_ALIASES = {
    "date": [
        "date", "transaction date", "txn date",
        "trans date", "posting date",
    ],
    "value_date": [
        "value date", "val date", "value dt",
    ],
    "description": [
        "description", "particulars", "narration",
        "transaction details", "transaction description",
        "remarks", "details",
    ],
    "cheque_number": [
        "cheque no", "cheque number", "chq no",
        "check number", "instrument number",
    ],
    "debit": [
        "debit", "withdrawal", "withdrawals", "dr",
        "amount debited", "debit amount",
    ],
    "credit": [
        "credit", "deposit", "deposits", "cr",
        "amount credited", "credit amount",
    ],
    "balance": [
        "balance", "closing balance",
        "running balance", "available balance",
    ],
    "amount": [
        "amount", "transaction amount", "txn amount",
    ],
}


def _normalize_header_text(text):
    """Normalize header text for reliable matching."""

    text = str(text).lower()
    text = text.replace("_", " ").replace("-", " ")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def _find_columns(header_text):
    """Identify recognized column names in a header."""

    normalized_text = _normalize_header_text(header_text)
    detected_columns = {}

    for column_name, aliases in COLUMN_ALIASES.items():

        for alias in sorted(aliases, key=len, reverse=True):
            normalized_alias = _normalize_header_text(alias)

            pattern = (
                r"(?<![a-z0-9])"
                + re.escape(normalized_alias)
                + r"(?![a-z0-9])"
            )

            match = re.search(pattern, normalized_text)

            if match:
                detected_columns[column_name] = {
                    "matched_label": alias,
                    "position": match.start(),
                }
                break

    return detected_columns


def _evaluate_header(header_text):
    """Score a possible transaction header."""

    columns = _find_columns(header_text)
    score = 0

    score_weights = {
        "date": 2,
        "description": 2,
        "debit": 1,
        "credit": 1,
        "balance": 2,
        "amount": 1,
        "value_date": 1,
        "cheque_number": 1,
    }

    for column_name, weight in score_weights.items():
        if column_name in columns:
            score += weight

    return score, columns


def _make_result(
    recognized,
    header_text=None,
    line_number=None,
    line_count=None,
    columns=None,
    score=0,
    warnings=None,
):
    """Build a consistent detector response."""

    columns = columns or {}
    warnings = warnings or []

    if recognized and "balance" not in columns:
        warnings.append(
            "Running balance column was not detected."
        )

    if (
        recognized
        and "amount" in columns
        and "debit" not in columns
        and "credit" not in columns
    ):
        warnings.append(
            "Generic amount column detected. "
            "Transaction direction must be determined separately."
        )

    if recognized and "value_date" in columns:
        warnings.append(
            "Both transaction date and value date may be present. "
            "Use transaction date as the primary date unless "
            "the statement layout requires otherwise."
        )

    if not recognized and header_text:
        warnings.append(
            "Detected columns are insufficient to confirm "
            "a transaction table layout."
        )

    return {
        "success": True,
        "recognized": recognized,
        "layout_type": (
            "structured_bank_statement"
            if recognized
            else (
                "partially_recognized"
                if header_text
                else "unknown"
            )
        ),
        "header_line": header_text,
        "header_line_number": line_number,
        "header_line_count": line_count,
        "columns": columns,
        "column_names": list(columns.keys()),
        "confidence": round(min(score / 8, 1.0), 2),
        "warnings": warnings,
        "error": None,
    }


def detect_statement_layout(text):
    """
    Detect the transaction table layout in extracted statement text.

    Single-line headers are checked first. Multi-line detection
    is attempted only when no complete single-line header exists.

    This function does not extract or save transactions.
    """

    if not isinstance(text, str) or not text.strip():
        return {
            "success": False,
            "recognized": False,
            "layout_type": "unknown",
            "header_line": None,
            "header_line_number": None,
            "columns": {},
            "column_names": [],
            "confidence": 0.0,
            "warnings": [],
            "error": "Input text is empty or invalid.",
        }

    # Keep original line numbers but ignore blank lines.
    nonempty_lines = [
        (index + 1, line.strip())
        for index, line in enumerate(text.splitlines())
        if line.strip()
    ]

    best_candidate = None
    best_score = 0

    # Pass 1: inspect individual lines.
    for line_number, line in nonempty_lines:
        score, columns = _evaluate_header(line)

        if score > best_score:
            best_score = score
            best_candidate = {
                "header_text": line,
                "line_number": line_number,
                "line_count": 1,
                "columns": columns,
            }

        # Prefer a complete single-line header.
        if (
            "date" in columns
            and "description" in columns
            and any(
                field in columns
                for field in ["debit", "credit", "amount"]
            )
        ):
            return _make_result(
                recognized=True,
                header_text=line,
                line_number=line_number,
                line_count=1,
                columns=columns,
                score=score,
            )

    # Pass 2: inspect adjacent nonempty lines only if necessary.
    for index in range(len(nonempty_lines)):

        for line_count in (2, 3):
            group = nonempty_lines[index:index + line_count]

            if len(group) != line_count:
                continue

            candidate_text = " ".join(
                line for _, line in group
            )

            score, columns = _evaluate_header(candidate_text)

            if score > best_score:
                best_score = score
                best_candidate = {
                    "header_text": candidate_text,
                    "line_number": group[0][0],
                    "line_count": line_count,
                    "columns": columns,
                }

    if best_candidate is None:
        return _make_result(recognized=False)

    columns = best_candidate["columns"]

    recognized = (
        "date" in columns
        and "description" in columns
        and any(
            field in columns
            for field in ["debit", "credit", "amount"]
        )
    )

    return _make_result(
        recognized=recognized,
        header_text=best_candidate["header_text"],
        line_number=best_candidate["line_number"],
        line_count=best_candidate["line_count"],
        columns=columns,
        score=best_score,
    )
