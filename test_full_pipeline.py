
"""
FINWELL AI — COMPLETE PIPELINE TEST
Version: 2.0

Tests:
1. PDF validation
2. PDF text extraction
3. Text cleaning
4. Document classification
5. Transaction parsing
6. Transaction normalization
7. Transaction validation
8. Debit and credit calculation
9. Running balance reconciliation
10. JSON report generation

Run:
    python test_full_pipeline.py

Custom PDF:
    python test_full_pipeline.py --pdf "C:/path/to/statement.pdf"
"""

import argparse
import json
import sys
import traceback

from pathlib import Path
from datetime import datetime
from collections.abc import Mapping, Sequence
from decimal import Decimal, InvalidOperation


# ============================================================
# CONFIGURATION
# ============================================================

DEFAULT_PDF = Path(
    r"C:\Users\shaas\Downloads\finwell_reconciliation_secondary_complex_dec2026.pdf"
)

PROJECT_ROOT = Path(__file__).resolve().parent

REPORT_DIR = PROJECT_ROOT / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

REPORT_PATH = REPORT_DIR / "full_pipeline_report.json"

SUMMARY = {
    "pipeline_status": "NOT_STARTED",
    "pipeline_error": None,
    "pdf_path": None,
    "pdf_valid": False,
    "extracted_characters": 0,
    "cleaned_characters": 0,
    "document_type": None,
    "parsed_transactions": 0,
    "normalized_transactions": 0,
    "validated_transactions": 0,
    "total_debits": 0.0,
    "total_credits": 0.0,
    "opening_balance": None,
    "closing_balance": None,
    "calculated_closing_balance": None,
    "balance_difference": None,
    "running_balance_reconciliation": "NOT_CHECKED",
    "validation_result": None,
    "stages": {},
}


# ============================================================
# GENERAL UTILITIES
# ============================================================

def mark_stage(name, status, details=None):

    SUMMARY["stages"][name] = {
        "status": status,
        "details": details,
    }

    symbol = "[PASS]" if status == "PASS" else (
        "[FAIL]" if status == "FAIL" else "[INFO]"
    )

    print(f"{symbol} {name}")

    if details:
        print(f"       {details}")


def to_decimal(value):

    if value is None or value == "":
        return Decimal("0")

    if isinstance(value, bool):
        raise ValueError("Boolean cannot be treated as a transaction amount")

    try:
        if isinstance(value, str):
            value = (
                value.replace(",", "")
                .replace("₹", "")
                .replace("Rs.", "")
                .strip()
            )

        return Decimal(str(value))

    except (InvalidOperation, ValueError):
        raise ValueError(f"Invalid monetary value: {value!r}")


def json_safe(value):

    if isinstance(value, Decimal):
        return float(value)

    if isinstance(value, Path):
        return str(value)

    if isinstance(value, Mapping):
        return {
            str(key): json_safe(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]

    if isinstance(value, (str, int, float, bool)) or value is None:
        return value

    return str(value)


# ============================================================
# TEXT EXTRACTION FROM MODULE OUTPUTS
# ============================================================

TEXT_KEYS = (
    "cleaned_text",
    "extracted_text",
    "full_text",
    "raw_text",
    "processed_text",
    "normalized_text",
    "document_text",
    "page_text",
    "text",
    "content",
)


def extract_text(value, depth=0):

    if depth > 12:
        raise ValueError("Maximum nested output depth exceeded")

    if isinstance(value, str):
        return value

    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")

    if isinstance(value, Mapping):

        for key in TEXT_KEYS:

            if key in value:

                result = extract_text(
                    value[key],
                    depth + 1
                )

                if result.strip():
                    return result

        if "pages" in value:

            result = extract_text(
                value["pages"],
                depth + 1
            )

            if result.strip():
                return result

        raise TypeError(
            "Dictionary does not contain recognized text fields. "
            f"Available keys: {list(value.keys())}"
        )

    if isinstance(value, Sequence) and not isinstance(
        value, (str, bytes, bytearray)
    ):

        pieces = []

        for item in value:

            result = extract_text(
                item,
                depth + 1
            )

            if result.strip():
                pieces.append(result)

        return "\n".join(pieces)

    raise TypeError(
        f"Unsupported text output: {type(value).__name__}"
    )


# ============================================================
# TRANSACTION OUTPUT EXTRACTION
# ============================================================

def extract_transactions(output, stage_name):

    if isinstance(output, list):
        transactions = output

    elif isinstance(output, Mapping):

        transactions = output.get("transactions")

        if transactions is None:
            transactions = output.get("data")

        if transactions is None:
            raise TypeError(
                f"{stage_name} did not return a transactions/data list. "
                f"Available keys: {list(output.keys())}"
            )

    else:

        raise TypeError(
            f"{stage_name} returned unsupported output: "
            f"{type(output).__name__}"
        )

    if not isinstance(transactions, list):

        raise TypeError(
            f"{stage_name} transactions must be a list"
        )

    for index, transaction in enumerate(transactions):

        if not isinstance(transaction, Mapping):

            raise TypeError(
                f"Transaction {index + 1} is not a dictionary"
            )

    return transactions


# ============================================================
# FINANCIAL CALCULATIONS
# ============================================================

def calculate_totals(transactions):

    total_debits = Decimal("0")
    total_credits = Decimal("0")

    for transaction in transactions:

        debit = transaction.get("debit")
        credit = transaction.get("credit")

        if debit is not None:
            total_debits += abs(to_decimal(debit))

        if credit is not None:
            total_credits += abs(to_decimal(credit))

    return (
        total_debits.quantize(Decimal("0.01")),
        total_credits.quantize(Decimal("0.01")),
    )


def extract_opening_balance(text):

    """
    Extract opening balance from common bank statement formats.

    Supports:
        OPENING BALANCE
        75,851.00

    Does not guess if the value cannot be identified.
    """

    import re

    patterns = [
        r"OPENING\s+BALANCE\s*(?:[:\-]?\s*)"
        r"(?:₹\s*)?([\d,]+(?:\.\d{1,2})?)",

        r"OPENING\s+BALANCE\s*[\r\n]+"
        r"\s*(?:₹\s*)?([\d,]+(?:\.\d{1,2})?)",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE
        )

        if match:
            return to_decimal(match.group(1))

    return None


def calculate_running_balance(transactions, opening_balance):

    """
    Check whether each transaction produces its recorded balance.

    Uses:
        balance_after = previous_balance - debit + credit

    This assumes the statement records debit and credit separately.
    """

    if opening_balance is None:
        return {
            "checked": False,
            "status": "NOT_CHECKED",
            "reason": "Opening balance could not be extracted.",
            "mismatches": [],
            "calculated_closing_balance": None,
        }

    current_balance = opening_balance
    mismatches = []

    for index, transaction in enumerate(transactions):

        debit = transaction.get("debit")
        credit = transaction.get("credit")
        recorded_balance = transaction.get("balance")

        debit_amount = (
            abs(to_decimal(debit))
            if debit is not None
            else Decimal("0")
        )

        credit_amount = (
            abs(to_decimal(credit))
            if credit is not None
            else Decimal("0")
        )

        current_balance = (
            current_balance
            - debit_amount
            + credit_amount
        )

        if recorded_balance is not None:

            recorded = to_decimal(recorded_balance)

            difference = abs(
                current_balance - recorded
            )

            if difference > Decimal("0.01"):

                mismatches.append({
                    "transaction_number": index + 1,
                    "description": transaction.get("description"),
                    "expected_balance": float(current_balance),
                    "recorded_balance": float(recorded),
                    "difference": float(difference),
                })

    return {
        "checked": True,
        "status": "PASS" if not mismatches else "FAIL",
        "reason": None,
        "mismatches": mismatches,
        "calculated_closing_balance": float(current_balance),
    }


# ============================================================
# PIPELINE IMPORTS
# ============================================================

def load_pipeline_modules():

    """
    Imports based on the module paths used in the previous test.

    These are the project's existing integration points.
    """

    from pdf_extraction.pdf_validator import validate_pdf

    from pdf_extraction.pdf_reader import extract_pdf_text

    from pdf_extraction.document_classifier import classify_document

    from preprocessing.text_cleaner import clean_extracted_text

    from preprocessing.transaction_parser import parse_transactions

    from preprocessing.data_normalizer import normalize_transactions

    from preprocessing.data_validator import validate_transactions

    return {
        "validate_pdf": validate_pdf,
        "extract_pdf_text": extract_pdf_text,
        "classify_document": classify_document,
        "clean_extracted_text": clean_extracted_text,
        "parse_transactions": parse_transactions,
        "normalize_transactions": normalize_transactions,
        "validate_transactions": validate_transactions,
    }


# ============================================================
# MAIN PIPELINE
# ============================================================

def run_pipeline(pdf_path):

    print("\n" + "=" * 65)
    print("FINWELL AI — COMPLETE PIPELINE TEST")
    print("=" * 65)

    SUMMARY["pdf_path"] = str(pdf_path)

    if not pdf_path.exists():

        raise FileNotFoundError(
            f"PDF file not found: {pdf_path}"
        )

    modules = load_pipeline_modules()

    # --------------------------------------------------------
    # STAGE 1: PDF VALIDATION
    # --------------------------------------------------------

    validation_output = modules["validate_pdf"](
        str(pdf_path)
    )

    print("\nPDF validation output:")
    print(repr(validation_output)[:1000])

    if isinstance(validation_output, Mapping):

        pdf_valid = validation_output.get(
            "valid",
            validation_output.get(
                "is_valid",
                validation_output.get("success", False)
            )
        )

    else:

        pdf_valid = bool(validation_output)

    if not pdf_valid:

        raise ValueError(
            f"PDF validation failed: {validation_output!r}"
        )

    SUMMARY["pdf_valid"] = True

    mark_stage(
        "PDF Validation",
        "PASS"
    )

    # --------------------------------------------------------
    # STAGE 2: PDF TEXT EXTRACTION
    # --------------------------------------------------------

    extraction_output = modules["extract_pdf_text"](
        str(pdf_path)
    )

    extracted_text = extract_text(
        extraction_output
    )

    if not extracted_text.strip():

        raise ValueError(
            "PDF extraction returned empty text"
        )

    SUMMARY["extracted_characters"] = len(
        extracted_text
    )

    mark_stage(
        "PDF Text Extraction",
        "PASS",
        f"Extracted characters: {len(extracted_text)}"
    )

    # --------------------------------------------------------
    # STAGE 3: TEXT CLEANING
    # --------------------------------------------------------

    cleaning_output = modules["clean_extracted_text"](
        extracted_text
    )

    print("\nText cleaner output type:")
    print(type(cleaning_output).__name__)

    if isinstance(cleaning_output, Mapping):

        print(
            "Text cleaner output keys:",
            list(cleaning_output.keys())
        )

        if cleaning_output.get("success") is False:

            raise ValueError(
                f"Text cleaning failed: "
                f"{cleaning_output.get('error')}"
            )

    cleaned_text = extract_text(
        cleaning_output
    )

    if not cleaned_text.strip():

        raise ValueError(
            "Text cleaning returned empty content"
        )

    SUMMARY["cleaned_characters"] = len(
        cleaned_text
    )

    mark_stage(
        "Text Cleaning",
        "PASS",
        f"Cleaned characters: {len(cleaned_text)}"
    )

    # --------------------------------------------------------
    # STAGE 4: DOCUMENT CLASSIFICATION
    # --------------------------------------------------------

    classification_output = modules["classify_document"](
        cleaned_text
    )

    print("\nDocument classification:")
    print(repr(classification_output)[:1000])

    if isinstance(classification_output, Mapping):

        if classification_output.get("success") is False:

            raise ValueError(
                f"Classification failed: {classification_output}"
            )

        document_type = classification_output.get(
            "document_type",
            classification_output.get(
                "type",
                classification_output.get("label")
            )
        )

        confidence = classification_output.get(
            "confidence"
        )

    else:

        document_type = classification_output
        confidence = None

    SUMMARY["document_type"] = str(
        document_type
    )

    SUMMARY["classification_confidence"] = confidence

    mark_stage(
        "Document Classification",
        "PASS",
        f"Document type: {document_type}"
    )

    # --------------------------------------------------------
    # STAGE 5: TRANSACTION PARSING
    # --------------------------------------------------------

    parsing_output = modules["parse_transactions"](
        cleaned_text
    )

    print("\nTransaction parser output type:")
    print(type(parsing_output).__name__)

    if isinstance(parsing_output, Mapping):

        print(
            "Parser output keys:",
            list(parsing_output.keys())
        )

        if parsing_output.get("success") is False:

            raise ValueError(
                f"Transaction parsing failed: {parsing_output}"
            )

    parsed_transactions = extract_transactions(
        parsing_output,
        "Transaction parser"
    )

    SUMMARY["parsed_transactions"] = len(
        parsed_transactions
    )

    mark_stage(
        "Transaction Parsing",
        "PASS",
        f"Parsed transactions: {len(parsed_transactions)}"
    )

    # --------------------------------------------------------
    # STAGE 6: NORMALIZATION
    # --------------------------------------------------------

    normalization_output = modules["normalize_transactions"](
        parsed_transactions
    )

    if isinstance(normalization_output, Mapping):

        if normalization_output.get("success") is False:

            raise ValueError(
                f"Normalization failed: {normalization_output}"
            )

    normalized_transactions = extract_transactions(
        normalization_output,
        "Transaction normalizer"
    )

    SUMMARY["normalized_transactions"] = len(
        normalized_transactions
    )

    mark_stage(
        "Transaction Normalization",
        "PASS",
        f"Normalized transactions: {len(normalized_transactions)}"
    )

    # --------------------------------------------------------
    # STAGE 7: TRANSACTION VALIDATION
    # --------------------------------------------------------

    validation_result = modules["validate_transactions"](
        normalized_transactions
    )

    print("\nTransaction validation output:")
    print(repr(validation_result)[:2000])

    if not isinstance(validation_result, Mapping):

        raise TypeError(
            "Transaction validator must return a dictionary. "
            f"Received: {type(validation_result).__name__}"
        )

    if validation_result.get("success") is False:

        raise ValueError(
            f"Transaction validation failed: {validation_result}"
        )

    valid_transactions = validation_result.get(
        "valid_transactions"
    )

    if not isinstance(valid_transactions, list):

        raise TypeError(
            "Validator did not return a valid_transactions list"
        )

    SUMMARY["validated_transactions"] = len(
        valid_transactions
    )

    SUMMARY["validation_result"] = "SUCCESS"

    if len(valid_transactions) != len(normalized_transactions):

        raise ValueError(
            "Transaction count mismatch: "
            f"{len(normalized_transactions)} normalized, "
            f"{len(valid_transactions)} validated"
        )

    mark_stage(
        "Transaction Validation",
        "PASS",
        f"Validated transactions: {len(valid_transactions)}"
    )

    # Use validated output for subsequent financial calculations.
    normalized_transactions = valid_transactions

    # --------------------------------------------------------
    # STAGE 8: FINANCIAL SUMMARY
    # --------------------------------------------------------

    total_debits, total_credits = calculate_totals(
        normalized_transactions
    )

    SUMMARY["total_debits"] = float(
        total_debits
    )

    SUMMARY["total_credits"] = float(
        total_credits
    )

    opening_balance = extract_opening_balance(
        cleaned_text
    )

    SUMMARY["opening_balance"] = (
        float(opening_balance)
        if opening_balance is not None
        else None
    )

    calculated_closing = None

    if opening_balance is not None:

        calculated_closing = (
            opening_balance
            - total_debits
            + total_credits
        )

        SUMMARY["calculated_closing_balance"] = float(
            calculated_closing
        )

    mark_stage(
        "Financial Summary",
        "PASS",
        (
            f"Debits: ₹{total_debits:,.2f} | "
            f"Credits: ₹{total_credits:,.2f}"
        )
    )

    # --------------------------------------------------------
    # STAGE 9: RUNNING BALANCE RECONCILIATION
    # --------------------------------------------------------

    reconciliation = calculate_running_balance(
        normalized_transactions,
        opening_balance
    )

    SUMMARY["running_balance_reconciliation"] = (
        reconciliation["status"]
    )

    SUMMARY["reconciliation_details"] = reconciliation

    SUMMARY["calculated_closing_balance"] = (
        reconciliation["calculated_closing_balance"]
    )

    if reconciliation["checked"]:

        closing_balance = (
            reconciliation["calculated_closing_balance"]
        )

        SUMMARY["closing_balance"] = closing_balance

        if reconciliation["status"] == "PASS":

            mark_stage(
                "Running Balance Reconciliation",
                "PASS",
                "All available transaction balances match."
            )

        else:

            mark_stage(
                "Running Balance Reconciliation",
                "FAIL",
                (
                    f"{len(reconciliation['mismatches'])} "
                    "balance mismatches detected."
                )
            )

    else:

        mark_stage(
            "Running Balance Reconciliation",
            "INFO",
            reconciliation["reason"]
        )

    # --------------------------------------------------------
    # FINAL STATUS
    # --------------------------------------------------------

    SUMMARY["pipeline_status"] = "SUCCESS"

    print("\n" + "=" * 65)
    print("PIPELINE EXECUTION COMPLETED")
    print("=" * 65)

    print(f"PDF: {pdf_path.name}")

    print(
        f"Parsed transactions: "
        f"{SUMMARY['parsed_transactions']}"
    )

    print(
        f"Normalized transactions: "
        f"{SUMMARY['normalized_transactions']}"
    )

    print(
        f"Validated transactions: "
        f"{SUMMARY['validated_transactions']}"
    )

    print(
        f"Total debits: ₹{total_debits:,.2f}"
    )

    print(
        f"Total credits: ₹{total_credits:,.2f}"
    )

    print(
        "Running balance reconciliation:",
        SUMMARY["running_balance_reconciliation"]
    )

    return normalized_transactions


# ============================================================
# REPORT GENERATION
# ============================================================

def save_report():

    SUMMARY["completed_at"] = datetime.now().isoformat()

    with REPORT_PATH.open(
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            json_safe(SUMMARY),
            file,
            indent=4,
            ensure_ascii=False
        )

    print(
        f"\nReport saved: {REPORT_PATH}"
    )


# ============================================================
# ENTRY POINT
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description="FinWell AI full pipeline test"
    )

    parser.add_argument(
        "--pdf",
        type=str,
        default=str(DEFAULT_PDF),
        help="Bank statement PDF path"
    )

    args = parser.parse_args()

    pdf_path = Path(args.pdf)

    try:

        run_pipeline(pdf_path)

    except Exception as exc:

        SUMMARY["pipeline_status"] = "FAILED"
        SUMMARY["pipeline_error"] = repr(exc)

        mark_stage(
            "Pipeline Execution",
            "FAIL",
            repr(exc)
        )

        traceback.print_exc()

    finally:

        save_report()

    if SUMMARY["pipeline_status"] != "SUCCESS":

        sys.exit(1)


if __name__ == "__main__":
    main()
