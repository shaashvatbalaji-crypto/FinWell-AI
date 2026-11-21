"""
FinWell AI transaction parser.

Designed for bank-statement text extraction where PDF tables may be emitted
as columnar text (one cell per line) rather than one transaction per line.

Safety rules:
- Monetary values are Decimal, never float.
- A transaction row must have a serial number and transaction date(s).
- Reference IDs are not treated as amounts.
- When debit/credit cells disappear from extracted text, the transaction
  amount is classified using the change in consecutive running balances.
- If direction cannot be established, it is flagged for review.
"""
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

CENT = Decimal("0.01")

DATE_RE = re.compile(
    r"^(?:\d{2}[/-]\d{2}[/-]\d{4}|"
    r"\d{2}-[A-Za-z]{3}-\d{4}|"
    r"\d{4}-\d{2}-\d{2}|"
    r"\d{2}[/-]\d{2}[/-]\d{2})$"
)
SERIAL_RE = re.compile(r"^\s*(\d{1,3})\s*$")
REF_RE = re.compile(r"^[A-Z]{2,8}\d{6,}[A-Z0-9]*$", re.I)
MONEY_RE = re.compile(
    r"^(?:₹|â‚¹|Rs\.?\s*)?"
    r"(?P<value>\(?-?\d[\d,]*(?:\.\d{1,2})?\)?|—|–|-|\?)$",
    re.I,
)
BOUNDARY_RE = re.compile(
    r"^(?:OPENING\s+BALANCE|CLOSING\s+BALANCE|STATEMENT\s+SUMMARY|"
    r"TRANSACTION\s+DETAILS|TOTAL\s+DEPOSITS|TOTAL\s+WITHDRAWALS|"
    r"TOTAL\s+CREDITS|TOTAL\s+DEBITS|END\s+OF\s+STATEMENT)\b",
    re.I,
)
DEBIT_HINTS = re.compile(
    r"\b(?:DR|DEBIT|PURCHASE|WDL|WITHDRAWAL|PAYMENT|EMI|BILLPAY|"
    r"TO SELF|FEE|CHARGES|TRANSFER TO|PAID TO|RECHARGE)\b", re.I
)
CREDIT_HINTS = re.compile(
    r"\b(?:CR|CREDIT|SALARY|DEPOSIT|REFUND|REVERSAL|INTEREST|"
    r"CASHBACK|TRANSFER FROM|RECEIVED FROM)\b", re.I
)


def normalize_date(value):
    if not isinstance(value, str):
        return None
    value = value.strip()
    for fmt in (
        "%d-%b-%Y", "%d-%B-%Y", "%d-%m-%Y", "%d/%m/%Y",
        "%Y-%m-%d", "%d-%m-%y", "%d/%m/%y",
    ):
        try:
            return datetime.strptime(value, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def parse_amount(value):
    if value is None:
        return None
    text = str(value).strip().replace("₹", "").replace("â‚¹", "")
    text = re.sub(r"^Rs\.?\s*", "", text, flags=re.I).replace(",", "").strip()
    if text in {"", "—", "–", "-", "?"}:
        return None
    paren_negative = text.startswith("(") and text.endswith(")")
    if paren_negative:
        text = text[1:-1].strip()
    try:
        number = Decimal(text)
        if paren_negative:
            number = -abs(number)
        if not number.is_finite():
            return None
        return number.quantize(CENT, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError):
        return None


def _is_money_cell(line):
    return bool(MONEY_RE.fullmatch(line.strip()))


def _is_reference(line):
    return bool(REF_RE.fullmatch(line.strip()))


def _classify_by_balance(amount, balance, previous_balance, description):
    if amount is None:
        return None, None, False

    amount = abs(amount)
    if previous_balance is not None and balance is not None:
        delta = (balance - previous_balance).quantize(CENT)
        if delta == -amount:
            return amount, None, True
        if delta == amount:
            return None, amount, True
        return None, None, False

    debit_hint = bool(DEBIT_HINTS.search(description))
    credit_hint = bool(CREDIT_HINTS.search(description))
    if debit_hint and not credit_hint:
        return amount, None, True
    if credit_hint and not debit_hint:
        return None, amount, True
    return None, None, False


def _build_transaction(block, previous_balance):
    # A valid block starts with a serial number, followed by transaction date.
    if len(block) < 4 or not SERIAL_RE.fullmatch(block[0]):
        return None

    date_positions = []
    for index, item in enumerate(block[1:], start=1):
        if DATE_RE.fullmatch(item.strip()):
            normalized = normalize_date(item)
            if normalized:
                date_positions.append((index, normalized))

    # This statement has transaction date + value date. Requiring both
    # prevents statement-period/header dates from becoming transactions.
    if len(date_positions) < 2:
        return None

    date_index, transaction_date = date_positions[0]
    second_date_index = date_positions[1][0]

    description_parts = []
    money_values = []
    for index, item in enumerate(block[second_date_index + 1:], start=second_date_index + 1):
        value = item.strip()
        if not value or _is_reference(value):
            continue
        if _is_money_cell(value):
            money_values.append(parse_amount(value))
            continue
        if BOUNDARY_RE.match(value):
            continue
        # Exclude repeated page headers, column headings and footers that
        # can appear between transactions when a PDF spans multiple pages.
        if re.search(
            r"synthetic statement generated|page \d+ of \d+|"
            r"^meridian crest bank$|^trusted banking|^statement of account$|"
            r"^account x{2,}|^sr$|^txn date$|^value date$|^description$|"
            r"^ref no\.?$|^debit \(₹\)$|^credit \(₹\)$|^balance \(₹\)$",
            value, re.I,
        ):
            continue
        description_parts.append(value)

    description = " ".join(description_parts).strip()
    if not description or not money_values:
        return None

    # The final monetary cell is the running balance. In this PDF, blank
    # debit/credit cells are omitted by text extraction, leaving:
    # [transaction amount, running balance].
    balance = money_values[-1]
    debit = credit = None
    certain = False

    if len(money_values) >= 3:
        # Explicit Debit, Credit, Balance columns when all cells are present.
        debit_value, credit_value, balance = money_values[-3:]
        debit = abs(debit_value) if debit_value is not None and debit_value != 0 else None
        credit = abs(credit_value) if credit_value is not None and credit_value != 0 else None
        certain = (debit is None) != (credit is None)
    elif len(money_values) >= 2:
        transaction_amount = money_values[-2]
        debit, credit, certain = _classify_by_balance(
            transaction_amount, balance, previous_balance, description
        )
    else:
        # A lone amount cannot be safely interpreted as both transaction and balance.
        return None

    return {
        "date": transaction_date,
        "description": description,
        "debit": debit,
        "credit": credit,
        "balance": balance,
        "direction_uncertain": not certain,
    }


def _parse_serial_blocks(lines):
    transactions = []
    previous_balance = None
    current_block = []

    def flush():
        nonlocal previous_balance
        if not current_block:
            return
        tx = _build_transaction(current_block, previous_balance)
        if tx is not None:
            transactions.append(tx)
            if tx["balance"] is not None:
                previous_balance = tx["balance"]
        current_block.clear()

    for raw in lines:
        line = raw.strip()
        if not line:
            continue

        if SERIAL_RE.fullmatch(line):
            flush()
            current_block.append(line)
            continue

        if BOUNDARY_RE.match(line):
            flush()
            continue

        if current_block:
            current_block.append(line)

    flush()
    return transactions


def _parse_inline_serial_rows(lines):
    """Fallback for extractors that put an entire numbered row on one line."""
    transactions = []
    previous_balance = None

    for raw in lines:
        line = raw.strip()
        match = re.match(r"^(\d{1,3})\s+(.+)$", line)
        if not match:
            continue
        remainder = match.group(2)
        tokens = re.split(r"\s{2,}|\s+\|\s+", remainder)
        # Parse only if at least two date tokens are explicitly present.
        date_tokens = [normalize_date(token.strip()) for token in tokens]
        valid_dates = [d for d in date_tokens if d]
        if len(valid_dates) < 2:
            continue

        date_positions = [
            i for i, token in enumerate(tokens)
            if normalize_date(token.strip())
        ]
        tail = tokens[date_positions[1] + 1:]
        desc_parts, money = [], []
        for token in tail:
            token = token.strip()
            if _is_reference(token):
                continue
            if _is_money_cell(token):
                money.append(parse_amount(token))
            elif token:
                desc_parts.append(token)

        if len(money) < 2:
            continue
        balance = money[-1]
        debit, credit, certain = _classify_by_balance(
            money[-2], balance, previous_balance, " ".join(desc_parts)
        )
        tx = {
            "date": valid_dates[0],
            "description": " ".join(desc_parts).strip(),
            "debit": debit,
            "credit": credit,
            "balance": balance,
            "direction_uncertain": not certain,
        }
        if tx["description"]:
            transactions.append(tx)
            previous_balance = balance

    return transactions


def parse_transactions(text):
    if not isinstance(text, str) or not text.strip():
        return {
            "success": False,
            "transactions": [],
            "total_transactions": 0,
            "uncertain_direction_count": 0,
            "error": "Input text must be a non-empty string.",
        }

    try:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        transactions = _parse_serial_blocks(lines)
        if not transactions:
            transactions = _parse_inline_serial_rows(lines)

        if not transactions:
            return {
                "success": False,
                "transactions": [],
                "total_transactions": 0,
                "uncertain_direction_count": 0,
                "error": "No numbered transaction rows could be parsed; review statement layout.",
            }

        uncertain = sum(bool(tx["direction_uncertain"]) for tx in transactions)
        return {
            "success": True,
            "transactions": transactions,
            "total_transactions": len(transactions),
            "uncertain_direction_count": uncertain,
            "error": None,
        }
    except Exception as exc:
        return {
            "success": False,
            "transactions": [],
            "total_transactions": 0,
            "uncertain_direction_count": 0,
            "error": str(exc),
        }
