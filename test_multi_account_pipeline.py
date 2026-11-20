"""FinWell AI multi-account pipeline with optional MySQL persistence."""

import argparse
import json
import sys
import traceback
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from test_full_pipeline import run_pipeline
from reconciliation.multi_account_reconciler import reconcile_multiple_accounts
from reconciliation_mysql_bridge import (
    persist_statement_transactions,
    persist_internal_transfer_matches,
)

PROJECT_ROOT = Path(__file__).resolve().parent
REPORT_DIR = PROJECT_ROOT / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)
REPORT_PATH = REPORT_DIR / "multi_account_pipeline_report.json"


def json_safe(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def parse_pairs(values):
    return {str(k): v for k, v in (values or [])}


def run_multi_account_pipeline(
    statements,
    account_names=None,
    mysql_account_ids=None,
    user_id=None,
    date_tolerance_days=2,
):
    if not statements:
        raise ValueError("Provide at least one --statement ACCOUNT_ID PDF.")

    account_names = account_names or {}
    mysql_account_ids = {str(k): int(v) for k, v in (mysql_account_ids or {}).items()}
    account_keys = [str(account_id) for account_id, _ in statements]
    mysql_enabled = user_id is not None or bool(mysql_account_ids)
    if mysql_enabled:
        if user_id is None:
            raise ValueError("--user-id is required when enabling MySQL persistence.")
        missing = [key for key in account_keys if key not in mysql_account_ids]
        if missing:
            raise ValueError("Missing --mysql-account-id mapping for: " + ", ".join(missing))

    combined_transactions = []
    statement_results = []
    account_metadata = []

    for external_account_id, pdf_text in statements:
        account_key = str(external_account_id)
        pdf_path = Path(pdf_text).expanduser()
        if not pdf_path.is_file():
            raise FileNotFoundError(f"Statement PDF not found: {pdf_path}")

        print("\n" + "=" * 72)
        print(f"PROCESSING ACCOUNT: {account_key}")
        print(f"PDF: {pdf_path}")
        print("=" * 72)

        validated = run_pipeline(pdf_path)
        if not isinstance(validated, list):
            raise TypeError(f"Pipeline for account {account_key} did not return a list.")

        persistence_info = None
        if mysql_enabled:
            persistence_info = persist_statement_transactions(
                user_id=user_id,
                mysql_account_id=mysql_account_ids[account_key],
                pdf_path=pdf_path,
                transactions=validated,
            )
            validated = persistence_info["transactions"]

        tagged = []
        for transaction in validated:
            item = dict(transaction)
            item["account_id"] = account_key
            tagged.append(item)
        combined_transactions.extend(tagged)

        account_metadata.append({
            "account_id": account_key,
            "account_name": account_names.get(account_key, f"Account {account_key}"),
            "currency": "INR",
        })
        statement_results.append({
            "account_id": account_key,
            "mysql_account_id": mysql_account_ids.get(account_key),
            "document_id": persistence_info["document_id"] if persistence_info else None,
            "pdf_path": str(pdf_path.resolve()),
            "validated_transaction_count": len(tagged),
            "mysql_persistence": {
                k: v for k, v in (persistence_info or {}).items() if k != "transactions"
            } if persistence_info else None,
        })

    print("\n" + "=" * 72)
    print("MULTI-ACCOUNT RECONCILIATION")
    print("=" * 72)
    result = reconcile_multiple_accounts(
        transactions=combined_transactions,
        accounts=account_metadata,
        date_tolerance_days=date_tolerance_days,
    )

    transfer_matches = result["transfer_reconciliation"]["matches"]
    mysql_persistence = {
        "enabled": mysql_enabled,
        "status": "NOT_REQUESTED",
        "attempted": 0,
        "saved_or_existing": 0,
        "failed": 0,
        "results": [],
    }
    if mysql_enabled:
        mysql_persistence = persist_internal_transfer_matches(user_id, transfer_matches)
        mysql_persistence["enabled"] = True
        mysql_persistence["status"] = "SUCCESS" if mysql_persistence["success"] else "FAILED"

    report = {
        "pipeline": "FinWell AI multi-account pipeline",
        "pipeline_status": "SUCCESS" if not mysql_enabled or mysql_persistence["success"] else "MYSQL_PERSISTENCE_FAILED",
        "statement_results": statement_results,
        "summary": result["summary"],
        "account_reports": result["account_reports"],
        "consolidated_report": result["consolidated_report"],
        "transfer_reconciliation": result["transfer_reconciliation"],
        "mysql_reconciliation_persistence": mysql_persistence,
    }
    with REPORT_PATH.open("w", encoding="utf-8") as handle:
        json.dump(json_safe(report), handle, indent=4, ensure_ascii=False)

    print("\nMULTI-ACCOUNT SUMMARY")
    print(json.dumps(json_safe(result["summary"]), indent=4))
    print("\nMATCHED INTERNAL TRANSFERS")
    print(json.dumps(json_safe(transfer_matches), indent=4))
    print("\nMYSQL RECONCILIATION PERSISTENCE")
    print(json.dumps(json_safe(mysql_persistence), indent=4))
    print(f"\nReport saved: {REPORT_PATH}")

    if mysql_enabled and not mysql_persistence["success"]:
        raise RuntimeError(
            f"Reconciliation completed, but {mysql_persistence['failed']} MySQL match(es) failed."
        )
    return report


def main():
    parser = argparse.ArgumentParser(
        description="Run FinWell multi-account reconciliation and optionally persist to MySQL."
    )
    parser.add_argument("--statement", nargs=2, action="append", metavar=("ACCOUNT_ID", "PDF_PATH"), required=True)
    parser.add_argument("--account-name", nargs=2, action="append", metavar=("ACCOUNT_ID", "NAME"))
    parser.add_argument("--mysql-account-id", nargs=2, action="append", metavar=("ACCOUNT_ID", "MYSQL_ACCOUNT_ID"), help="Map external statement account ID to existing MySQL account ID.")
    parser.add_argument("--user-id", type=int, help="FinWell user ID owning the MySQL accounts.")
    parser.add_argument("--date-tolerance-days", type=int, default=2)
    args = parser.parse_args()

    if args.date_tolerance_days < 0:
        parser.error("--date-tolerance-days cannot be negative.")
    ids = [str(item[0]) for item in args.statement]
    if len(ids) != len(set(ids)):
        parser.error("Each external account ID may be supplied only once.")
    try:
        run_multi_account_pipeline(
            statements=args.statement,
            account_names=parse_pairs(args.account_name),
            mysql_account_ids=parse_pairs(args.mysql_account_id),
            user_id=args.user_id,
            date_tolerance_days=args.date_tolerance_days,
        )
    except Exception as exc:
        print(f"\nMULTI-ACCOUNT PIPELINE FAILED: {exc}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
