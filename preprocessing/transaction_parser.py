import re
from datetime import datetime
from decimal import Decimal, InvalidOperation


DATE_PATTERN = re.compile(
    r"^\s*("
    r"\d{2}[/-]\d{2}[/-]\d{4}"
    r"|\d{4}-\d{2}-\d{2}"
    r"|\d{2}[/-]\d{2}[/-]\d{2}"
    r")\s*(.*)$"
)

AMOUNT_PATTERN = re.compile(
    r"^\s*(?:₹|Rs\.?\s*)?"
    r"(-?\d[\d,]*\.\d{2}|\(\d[\d,]*\.\d{2}\)|—|–|-|\?)"
    r"\s*$",
    re.IGNORECASE,
)

EMPTY_AMOUNT_VALUES = {"", "—", "–", "-", "?"}


def normalize_date(date_text: str) -> str | None:
    if not isinstance(date_text, str):
        return None

    date_text = date_text.strip()

    supported_formats = [
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%Y-%m-%d",
        "%d-%m-%y",
        "%d/%m/%y",
    ]

    for date_format in supported_formats:
        try:
            parsed_date = datetime.strptime(date_text, date_format)
            return parsed_date.strftime("%Y-%m-%d")
        except ValueError:
            continue

    return None


def parse_amount(amount_text: str | None) -> float | None:
    if amount_text is None:
        return None

    value = str(amount_text).strip()
    value = value.replace("₹", "")
    value = re.sub(r"Rs\.?", "", value, flags=re.IGNORECASE)
    value = value.replace(",", "").strip()

    if value in EMPTY_AMOUNT_VALUES:
        return None

    if value.startswith("(") and value.endswith(")"):
        value = "-" + value[1:-1]

    try:
        return float(value)
    except ValueError:
        return None


def _is_amount_line(line: str) -> bool:
    return bool(AMOUNT_PATTERN.match(line.strip()))


def _parse_amount_line(line: str) -> float | None:
    match = AMOUNT_PATTERN.match(line.strip())

    if not match:
        return None

    return parse_amount(match.group(1))


def _is_transaction_date_line(line: str) -> bool:
    return bool(DATE_PATTERN.match(line.strip()))


def _parse_multiline_rows(lines: list[str]) -> list[dict]:
    """
    Parse multiline statement rows.

    Handles rows where PDF text extraction omits empty Debit/Credit cells.
    When a row contains transaction amount + running balance, use the
    balance movement to infer debit or credit.
    """

    transactions = []
    index = 0
    previous_balance = None

    while index < len(lines):
        date_match = DATE_PATTERN.match(lines[index])

        if not date_match:
            index += 1
            continue

        date_text = date_match.group(1)
        remainder = date_match.group(2).strip()
        normalized_date = normalize_date(date_text)

        if not normalized_date:
            index += 1
            continue

        index += 1
        description_parts = []
        amounts = []

        if remainder:
            if _is_amount_line(remainder):
                amounts.append(_parse_amount_line(remainder))
            else:
                description_parts.append(remainder)

        while index < len(lines):
            current_line = lines[index].strip()

            if _is_transaction_date_line(current_line):
                break

            if _is_amount_line(current_line):
                amounts.append(_parse_amount_line(current_line))
                index += 1

                if len(amounts) >= 3:
                    break
            else:
                if current_line:
                    description_parts.append(current_line)
                index += 1

        description = " ".join(description_parts).strip()

        if not description or not amounts:
            continue

        if re.search(
            r"\b(opening|closing)\s+balance\b",
            description,
            re.IGNORECASE,
        ):
            continue

        debit = None
        credit = None
        balance = None

        # Three fields: debit, credit, balance.
        if len(amounts) >= 3:
            debit = amounts[0]
            credit = amounts[1]
            balance = amounts[2]

        # Two fields: transaction amount + balance.
        elif len(amounts) == 2:
            transaction_amount = amounts[0]
            balance = amounts[1]

            if transaction_amount is not None:
                if transaction_amount < 0:
                    debit = abs(transaction_amount)
                elif previous_balance is not None and balance is not None:
                    if balance < previous_balance:
                        debit = transaction_amount
                    elif balance > previous_balance:
                        credit = transaction_amount
                else:
                    # First transaction fallback: use description indicators.
                    if re.search(
                        r"\b(DR|DEBIT|PURCHASE|WDL|WITHDRAWAL|PAYMENT|"
                        r"EMI|BILLPAY|TO SELF)\b",
                        description,
                        re.IGNORECASE,
                    ):
                        debit = transaction_amount
                    else:
                        credit = transaction_amount

        # One field: transaction amount only.
        elif len(amounts) == 1:
            transaction_amount = amounts[0]

            if transaction_amount is not None:
                if transaction_amount < 0:
                    debit = abs(transaction_amount)
                elif re.search(
                    r"\b(DR|DEBIT|PURCHASE|WDL|WITHDRAWAL|PAYMENT|"
                    r"EMI|BILLPAY|TO SELF)\b",
                    description,
                    re.IGNORECASE,
                ):
                    debit = transaction_amount
                else:
                    credit = transaction_amount

        transactions.append({
            "date": normalized_date,
            "description": description,
            "debit": debit,
            "credit": credit,
            "balance": balance,
        })

        if balance is not None:
            previous_balance = balance

    return transactions


def _parse_single_line_rows(lines: list[str]) -> list[dict]:
    transactions = []
    previous_balance = None

    for line in lines:
        date_match = DATE_PATTERN.match(line.strip())

        if not date_match:
            continue

        date_text = date_match.group(1)
        remainder = date_match.group(2).strip()
        normalized_date = normalize_date(date_text)

        if not normalized_date or not remainder:
            continue

        amount_matches = re.findall(
            r"(?<!\w)(?:₹|Rs\.?\s*)?"
            r"(-?\d[\d,]*\.\d{2}|\(\d[\d,]*\.\d{2}\)|—|–|-|\?)",
            remainder,
            flags=re.IGNORECASE,
        )

        if not amount_matches:
            continue

        amounts = [parse_amount(value) for value in amount_matches]
        description = remainder

        for amount_text in reversed(amount_matches):
            description = re.sub(
                re.escape(amount_text) + r"\s*$",
                "",
                description,
                count=1,
            ).strip()

        if re.search(
            r"\b(opening|closing)\s+balance\b",
            description,
            re.IGNORECASE,
        ):
            continue

        debit = None
        credit = None
        balance = None

        if len(amounts) >= 3:
            debit = amounts[-3]
            credit = amounts[-2]
            balance = amounts[-1]

        elif len(amounts) == 2:
            transaction_amount = amounts[-2]
            balance = amounts[-1]

            if transaction_amount is not None:
                if transaction_amount < 0:
                    debit = abs(transaction_amount)
                elif previous_balance is not None and balance is not None:
                    if balance < previous_balance:
                        debit = transaction_amount
                    elif balance > previous_balance:
                        credit = transaction_amount
                else:
                    if re.search(
                        r"\b(DR|DEBIT|PURCHASE|WDL|WITHDRAWAL|PAYMENT|"
                        r"EMI|BILLPAY|TO SELF)\b",
                        description,
                        re.IGNORECASE,
                    ):
                        debit = transaction_amount
                    else:
                        credit = transaction_amount

        elif len(amounts) == 1:
            transaction_amount = amounts[0]

            if transaction_amount is not None:
                if transaction_amount < 0:
                    debit = abs(transaction_amount)
                elif re.search(
                    r"\b(DR|DEBIT|PURCHASE|WDL|WITHDRAWAL|PAYMENT|"
                    r"EMI|BILLPAY|TO SELF)\b",
                    description,
                    re.IGNORECASE,
                ):
                    debit = transaction_amount
                else:
                    credit = transaction_amount

        if not description:
            continue

        transactions.append({
            "date": normalized_date,
            "description": description,
            "debit": debit,
            "credit": credit,
            "balance": balance,
        })

        if balance is not None:
            previous_balance = balance

    return transactions


def parse_transactions(text: str) -> dict:
    if not isinstance(text, str):
        return {
            "success": False,
            "transactions": [],
            "total_transactions": 0,
            "error": "Input must be a string.",
        }

    if not text.strip():
        return {
            "success": False,
            "transactions": [],
            "total_transactions": 0,
            "error": "Input text is empty.",
        }

    try:
        lines = [
            line.strip()
            for line in text.splitlines()
            if line.strip()
        ]

        transactions = _parse_multiline_rows(lines)

        if not transactions:
            transactions = _parse_single_line_rows(lines)

        return {
            "success": True,
            "transactions": transactions,
            "total_transactions": len(transactions),
            "error": None,
        }

    except Exception as error:
        return {
            "success": False,
            "transactions": [],
            "total_transactions": 0,
            "error": str(error),
        }