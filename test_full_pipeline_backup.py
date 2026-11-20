"""
FinWell AI - Multi-account pipeline runner

Runs the existing single-PDF pipeline for each supplied statement, then
passes the validated transactions to the inter-account and multi-account
reconcilers.

This deliberately reuses test_full_pipeline.run_pipeline() so the existing
PDF extraction, cleaning, classification, parsing, normalization,
validation, and running-balance checks remain unchanged.

Usage (PowerShell):
    python test_multi_account_pipeline.py `
        --statement 4821 "C:/path/to/account_4821.pdf" `
        --statement 7392 "C:/path/to/account_7392.pdf"

Optional account labels:
    --account-name 4821 "Primary Savings"
    --account-name 7392 "Secondary Savings"
"""

import argparse
import json
import sys
import traceback
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from test_full_pipeline import run_pipeline

from reconciliation.multi_account_reconciler import (
    reconcile_multiple_accounts,
)


PROJECT_ROOT = Path(__file__).resolve().parent
REPORT_DIR = PROJECT_ROOT / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

REPORT_PATH = REPORT_DIR / "multi_account_pipeline_report.json"


def json_safe(value):
    """Convert Decimal/date/path values into JSON-compatible values."""
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def parse_account_names(values):
    """Parse repeated ACCOUNT_ID NAME arguments."""
    result = {}
    for account_id, name in values or []:
        result[str(account_id)] = name
    return result


def run_multi_account_pipeline(statements, account_names=None,
                                date_tolerance_days=2):
    """
    Run the existing full pipeline once per PDF, attach account IDs,
    and reconcile all validated transactions together.
    """
    if not statements:
        raise ValueError("Provide at least one --statement ACCOUNT_ID PDF.")

    account_names = account_names or {}
    combined_transactions = []
    account_metadata = []
    statement_results = []

    for account_id, pdf_path_text in statements:
        pdf_path = Path(pdf_path_text).expanduser()

        if not pdf_path.is_file():
            raise FileNotFoundError(f"Statement PDF not found: {pdf_path}")

        print("\n" + "=" * 72)
        print(f"PROCESSING ACCOUNT: {account_id}")
        print(f"PDF: {pdf_path}")
        print("=" * 72)

        # Existing pipeline performs validation, extraction, parsing,
        # normalization, transaction validation and running-balance checks.
        validated_transactions = run_pipeline(pdf_path)

        if not isinstance(validated_transactions, list):
            raise TypeError(
                f"Pipeline for account {account_id} did not return a list."
            )

        tagged_transactions = []

        for transaction in validated_transactions:
            if not isinstance(transaction, dict):
                transaction = dict(transaction)

            # Copy instead of mutating the original pipeline result.
            tagged = dict(transaction)
            tagged["account_id"] = str(account_id)
            tagged_transactions.append(tagged)

        combined_transactions.extend(tagged_transactions)

        account_metadata.append({
            "account_id": str(account_id),
            "account_name": account_names.get(
                str(account_id), f"Account {account_id}"
            ),
            "currency": "INR",
        })

        statement_results.append({
            "account_id": str(account_id),
            "pdf_path": str(pdf_path),
            "validated_transaction_count": len(tagged_transactions),
        })

    print("\n" + "=" * 72)
    print("MULTI-ACCOUNT RECONCILIATION")
    print("=" * 72)

    result = reconcile_multiple_accounts(
        transactions=combined_transactions,
        accounts=account_metadata,
        date_tolerance_days=date_tolerance_days,
    )

    report = {
        "pipeline": "FinWell AI multi-account pipeline",
        "pipeline_status": "SUCCESS",
        "statement_results": statement_results,
        "summary": result["summary"],
        "account_reports": result["account_reports"],
        "consolidated_report": result["consolidated_report"],
        "transfer_reconciliation": result["transfer_reconciliation"],
    }

    with REPORT_PATH.open("w", encoding="utf-8") as file:
        json.dump(
            json_safe(report),
            file,
            indent=4,
            ensure_ascii=False,
        )

    print("\nMULTI-ACCOUNT SUMMARY")
    print(json.dumps(json_safe(result["summary"]), indent=4))

    print("\nACCOUNT-WISE REPORT")
    print(json.dumps(json_safe(result["account_reports"]), indent=4))

    print("\nCONSOLIDATED REPORT")
    print(json.dumps(json_safe(result["consolidated_report"]), indent=4))

    print("\nMATCHED INTERNAL TRANSFERS")
    print(json.dumps(
        json_safe(result["transfer_reconciliation"]["matches"]),
        indent=4,
    ))

    print("\nAMBIGUOUS TRANSFERS - REVIEW REQUIRED")
    print(json.dumps(
        json_safe(
            result["transfer_reconciliation"]["ambiguous_transactions"]
        ),
        indent=4,
    ))

    print(f"\nReport saved: {REPORT_PATH}")
    return report


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Run FinWell's existing PDF pipeline on multiple bank "
            "statements and reconcile accounts together."
        )
    )

    parser.add_argument(
        "--statement",
        nargs=2,
        action="append",
        metavar=("ACCOUNT_ID", "PDF_PATH"),
        required=True,
        help=(
            "Account ID and statement PDF. Repeat this option for "
            "each account."
        ),
    )

    parser.add_argument(
        "--account-name",
        nargs=2,
        action="append",
        metavar=("ACCOUNT_ID", "NAME"),
        help="Optional account display name. May be repeated.",
    )

    parser.add_argument(
        "--date-tolerance-days",
        type=int,
        default=2,
        help="Maximum date difference allowed for transfer matching.",
    )

    args = parser.parse_args()

    if args.date_tolerance_days < 0:
        parser.error("--date-tolerance-days cannot be negative.")

    # Prevent duplicate account IDs: a single statement is expected
    # for each account in this runner.
    account_ids = [str(item[0]) for item in args.statement]
    if len(account_ids) != len(set(account_ids)):
        parser.error("Each account ID may be supplied only once.")

    try:
        run_multi_account_pipeline(
            statements=args.statement,
            account_names=parse_account_names(args.account_name),
            date_tolerance_days=args.date_tolerance_days,
        )
    except Exception as exc:
        print(f"\nMULTI-ACCOUNT PIPELINE FAILED: {exc}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
