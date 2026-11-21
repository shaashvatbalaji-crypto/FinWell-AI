"""
FinWell AI - complete pipeline validation runner.
This is a test harness only; it does not write to MySQL or ChromaDB.
Run: python test_full_pipeline.py --pdf "C:/path/to/statement.pdf"
"""
import argparse
import json
import re
import traceback
from pathlib import Path
from collections.abc import Mapping, Sequence
from decimal import Decimal, InvalidOperation

from preprocessing.transaction_parser import parse_transactions
from preprocessing.data_normalizer import normalize_transactions
from preprocessing.data_validator import validate_transactions

ROOT = Path(__file__).resolve().parent
REPORT_DIR = ROOT / "reports"
REPORT_DIR.mkdir(exist_ok=True)
REPORT_PATH = REPORT_DIR / "full_pipeline_report.json"
TRANSACTION_AUDIT_PATH = REPORT_DIR / "transaction_audit_report.json"


def extract_text(value, depth=0):
    if depth > 12:
        raise ValueError("Maximum nested output depth exceeded")
    if isinstance(value, str):
        return value
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, Mapping):
        for key in ("cleaned_text", "extracted_text", "full_text", "raw_text",
                    "processed_text", "normalized_text", "document_text",
                    "page_text", "text", "content"):
            if key in value:
                result = extract_text(value[key], depth + 1)
                if result.strip():
                    return result
        if "pages" in value:
            return extract_text(value["pages"], depth + 1)
        raise TypeError(f"No recognized text field in {list(value)}")
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return "\n".join(extract_text(item, depth + 1) for item in value)
    raise TypeError(f"Unsupported text result: {type(value).__name__}")


def to_decimal(value):
    if value is None:
        return Decimal("0.00")
    try:
        result = Decimal(str(value))
        if not result.is_finite():
            raise ValueError("Non-finite amount")
        return result
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"Invalid monetary value: {value!r}") from exc


def extract_statement_balance(text, label):
    # Conservative: accepts label followed by amount on same or next line.
    pattern = re.compile(
        rf"{label}\s*[:\-]?\s*(?:₹|â‚¹|Rs\.?\s*)?([\-]?\d[\d,]*(?:\.\d{{1,2}})?)",
        re.I
    )
    match = pattern.search(text)
    if not match:
        return None
    return to_decimal(match.group(1).replace(",", ""))


def check_running_balances(transactions, opening_balance, tolerance=Decimal("0.01")):
    result = {"status": "NOT_CHECKED", "checked_rows": 0, "mismatches": [],
              "calculated_closing_balance": None, "reason": None}
    if opening_balance is None:
        result["reason"] = "Opening balance not identified."
        return result
    if not transactions:
        result["reason"] = "No validated transactions."
        return result
    if not any(t.get("balance") is not None for t in transactions):
        result["reason"] = "No transaction running balances are available."
        return result

    current = opening_balance
    for idx, tx in enumerate(transactions, start=1):
        current = current - to_decimal(tx.get("debit")) + to_decimal(tx.get("credit"))
        recorded = tx.get("balance")
        if recorded is not None:
            result["checked_rows"] += 1
            difference = abs(current - to_decimal(recorded))
            if difference > tolerance:
                result["mismatches"].append({
                    "row": idx, "description": tx.get("description"),
                    "calculated": str(current), "recorded": str(to_decimal(recorded)),
                    "difference": str(difference)
                })
    result["calculated_closing_balance"] = str(current)
    if result["checked_rows"] == 0:
        result["reason"] = "No rows with recorded balances were checked."
    else:
        result["status"] = "PASS" if not result["mismatches"] else "FAIL"
    return result


def json_safe(obj):
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, dict):
        return {str(k): json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [json_safe(v) for v in obj]
    return obj


def run_pipeline(pdf_path):
    report = {
        "pipeline_status": "FAILED", "pdf_path": str(pdf_path),
        "stages": {}, "parsed_transactions": 0, "normalized_transactions": 0,
        "validated_transactions": 0, "invalid_transactions": [],
        "total_debits": "0.00", "total_credits": "0.00",
        "opening_balance": None, "statement_closing_balance": None,
        "calculated_closing_balance": None, "running_balance_reconciliation": None
    }

    def stage(name, status, details=None):
        report["stages"][name] = {"status": status, "details": details}
        print(f"[{status}] {name}" + (f" — {details}" if details else ""))

    try:
        if not pdf_path.is_file():
            raise FileNotFoundError(pdf_path)

        from pdf_extraction.pdf_validator import validate_pdf
        from pdf_extraction.pdf_reader import extract_pdf_text
        from pdf_extraction.document_classifier import classify_document
        from preprocessing.text_cleaner import clean_extracted_text

        pdf_result = validate_pdf(str(pdf_path))
        pdf_ok = (pdf_result.get("valid", pdf_result.get("is_valid",
                   pdf_result.get("success", False))) if isinstance(pdf_result, Mapping)
                  else bool(pdf_result))
        if not pdf_ok:
            raise ValueError(f"PDF validation failed: {pdf_result}")
        stage("PDF Validation", "PASS")

        extracted = extract_text(extract_pdf_text(str(pdf_path)))
        if not extracted.strip():
            raise ValueError("PDF extraction returned no text.")
        stage("PDF Text Extraction", "PASS", f"{len(extracted)} characters")

        cleaned_output = clean_extracted_text(extracted)
        if isinstance(cleaned_output, Mapping) and cleaned_output.get("success") is False:
            raise ValueError(f"Text cleaning failed: {cleaned_output}")
        cleaned = extract_text(cleaned_output)
        if not cleaned.strip():
            raise ValueError("Text cleaner returned empty text.")
        stage("Text Cleaning", "PASS", f"{len(cleaned)} characters")

        classification = classify_document(cleaned)
        if isinstance(classification, Mapping):
            if classification.get("success") is False:
                raise ValueError(f"Classification failed: {classification}")
            report["document_type"] = classification.get(
                "document_type", classification.get("type", classification.get("label"))
            )
        else:
            report["document_type"] = str(classification)
        stage("Document Classification", "PASS", str(report["document_type"]))

        parsed = parse_transactions(cleaned)
        if not parsed["success"]:
            raise ValueError(parsed.get("error") or "Parsing failed.")
        transactions = parsed["transactions"]
        report["parsed_transactions"] = len(transactions)
        # Preserve row-level output so it can be independently audited against the PDF.
        report["parsed_transaction_details"] = json_safe(transactions)
        stage("Transaction Parsing", "PASS", f"{len(transactions)} rows")

        normalized_result = normalize_transactions(transactions)
        normalized = normalized_result["transactions"]
        report["normalized_transactions"] = len(normalized)
        report["normalization_errors"] = normalized_result.get("errors", [])
        report["normalized_transaction_details"] = json_safe(normalized)
        stage("Transaction Normalization",
              "PASS" if normalized_result["success"] else "WARN",
              f"{len(normalized)} rows; {normalized_result['invalid_count']} normalization errors")

        validation = validate_transactions(normalized)
        valid = validation["valid_transactions"]
        report["validated_transactions"] = len(valid)
        report["invalid_transactions"] = json_safe(validation["invalid_transactions"])
        report["validated_transaction_details"] = json_safe(valid)
        if not valid:
            raise ValueError("No valid transactions remain after validation.")
        stage("Transaction Validation",
              "PASS" if validation["success"] else "WARN",
              f"{len(valid)} valid; {validation['invalid_count']} need review")

        debits = sum((to_decimal(t["debit"]) for t in valid), Decimal("0.00"))
        credits = sum((to_decimal(t["credit"]) for t in valid), Decimal("0.00"))
        report["total_debits"] = str(debits)
        report["total_credits"] = str(credits)
        stage("Financial Totals", "PASS", f"debits={debits}; credits={credits}")

        opening = extract_statement_balance(cleaned, r"OPENING\s+BALANCE")
        closing = extract_statement_balance(cleaned, r"CLOSING\s+BALANCE")
        report["opening_balance"] = str(opening) if opening is not None else None
        report["statement_closing_balance"] = str(closing) if closing is not None else None

        reconciliation = check_running_balances(valid, opening)
        report["running_balance_reconciliation"] = reconciliation
        report["calculated_closing_balance"] = reconciliation["calculated_closing_balance"]

        if closing is not None and reconciliation["calculated_closing_balance"] is not None:
            diff = abs(closing - Decimal(reconciliation["calculated_closing_balance"]))
            report["closing_balance_difference"] = str(diff)
            report["statement_closing_balance_check"] = (
                "PASS" if diff <= Decimal("0.01") else "FAIL"
            )
        else:
            report["statement_closing_balance_check"] = "NOT_CHECKED"

        stage("Running Balance Check", reconciliation["status"],
              reconciliation.get("reason") or f"{reconciliation['checked_rows']} recorded balances checked")
        stage("Statement Closing Balance Check", report["statement_closing_balance_check"])

        # A pipeline with rejected/uncertain rows is not an overall PASS.
        all_checks_pass = (
            validation["success"]
            and reconciliation["status"] in ("PASS", "NOT_CHECKED")
            and report["statement_closing_balance_check"] in ("PASS", "NOT_CHECKED")
        )
        report["pipeline_status"] = "PASS" if all_checks_pass else "REVIEW_REQUIRED"

    except Exception as exc:
        report["pipeline_error"] = str(exc)
        report["traceback"] = traceback.format_exc()
        stage("Pipeline", "FAIL", str(exc))

    # Write a compact, dedicated transaction-level audit file as well as the full report.
    audit_report = {
        "pdf_path": str(pdf_path),
        "pipeline_status": report["pipeline_status"],
        "parsed_transaction_count": report.get("parsed_transactions", 0),
        "normalized_transaction_count": report.get("normalized_transactions", 0),
        "validated_transaction_count": report.get("validated_transactions", 0),
        "parsed_transactions": report.get("parsed_transaction_details", []),
        "normalized_transactions": report.get("normalized_transaction_details", []),
        "validated_transactions": report.get("validated_transaction_details", []),
        "invalid_transactions": report.get("invalid_transactions", []),
        "normalization_errors": report.get("normalization_errors", []),
    }
    TRANSACTION_AUDIT_PATH.write_text(
        json.dumps(json_safe(audit_report), indent=2), encoding="utf-8"
    )
    REPORT_PATH.write_text(json.dumps(json_safe(report), indent=2), encoding="utf-8")
    print(f"\nReport saved: {REPORT_PATH}")
    print(f"Transaction audit saved: {TRANSACTION_AUDIT_PATH}")
    print(f"Pipeline status: {report['pipeline_status']}")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", type=Path, required=True, help="Path to statement PDF")
    args = parser.parse_args()
    run_pipeline(args.pdf)
