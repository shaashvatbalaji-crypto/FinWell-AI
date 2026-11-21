
"""
FinWell AI - Unified MySQL Reconciliation Runner

Connects:
    MySQL transaction storage
        -> Transaction normalization
        -> Account metadata enrichment
        -> Unified reconciliation service
        -> Read-only reconciliation report

Safety:
    - No MySQL writes.
    - No ChromaDB writes.
    - No automatic confirmation or rejection.
    - Account ownership is NOT assumed to be verified.
"""

import argparse
import json
import sys

from decimal import Decimal, InvalidOperation

from mysql_pipeline.transaction_storage import (
    list_user_transactions,
)

from mysql_pipeline.account_storage import (
    list_user_accounts,
)

from reconciliation.unified_reconciliation_service import (
    reconcile_all_transactions,
)


# ============================================================
# CONFIGURATION
# ============================================================

DEFAULT_TRANSACTION_LIMIT = 500

TRANSFER_DATE_GAP_DAYS = 1
REFUND_DATE_GAP_DAYS = 90
SETTLEMENT_DATE_GAP_DAYS = 5


# ============================================================
# VALIDATION HELPERS
# ============================================================

def validate_user_id(user_id):
    if isinstance(user_id, bool) or not isinstance(user_id, int):
        raise ValueError("user_id must be an integer.")

    if user_id <= 0:
        raise ValueError("user_id must be greater than zero.")

    return user_id


def to_decimal(value, field_name):
    """
    Convert a MySQL numeric value to Decimal.

    SQL NULL is normalized to zero for debit/credit fields.
    Other invalid values raise an error.
    """

    if value is None:
        return Decimal("0.00")

    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as error:
        raise ValueError(
            f"Invalid {field_name} value: {value!r}"
        ) from error

    if not result.is_finite():
        raise ValueError(
            f"{field_name} must be a finite number."
        )

    return result


# ============================================================
# MYSQL RETRIEVAL
# ============================================================

def load_transactions(user_id):
    print("\n[1/4] Loading transactions from MySQL...")

    response = list_user_transactions(
        user_id,
        limit=DEFAULT_TRANSACTION_LIMIT,
        offset=0,
    )

    if not isinstance(response, dict):
        raise RuntimeError(
            "Transaction storage returned an unexpected response."
        )

    if not response.get("success"):
        raise RuntimeError(
            response.get(
                "message",
                "Transaction retrieval failed."
            )
        )

    transactions = response.get("transactions", [])

    if not isinstance(transactions, list):
        raise RuntimeError(
            "MySQL transaction response is not a list."
        )

    print("Transactions retrieved:", len(transactions))

    return transactions


def load_accounts(user_id):
    print("\n[2/4] Loading accounts from MySQL...")

    response = list_user_accounts(user_id)

    if not isinstance(response, dict):
        raise RuntimeError(
            "Account storage returned an unexpected response."
        )

    if not response.get("success"):
        raise RuntimeError(
            response.get(
                "message",
                "Account retrieval failed."
            )
        )

    accounts = response.get("accounts", [])

    if not isinstance(accounts, list):
        raise RuntimeError(
            "MySQL account response is not a list."
        )

    print("Accounts retrieved:", len(accounts))

    return accounts


# ============================================================
# ACCOUNT METADATA NORMALIZATION
# ============================================================

def prepare_accounts(accounts):
    """
    Create an account lookup keyed by account_id.

    Important:
        The current account retrieval function does not return
        an explicit ownership-verification status.

        Therefore, verified is deliberately False.
        The transfer matcher must send these records for review
        rather than assuming ownership has been independently
        verified.
    """

    account_map = {}

    for account in accounts:

        if not isinstance(account, dict):
            continue

        account_id = account.get("account_id")

        if account_id is None:
            continue

        prepared_account = dict(account)

        # Do not invent or assume verification.
        prepared_account["verified"] = False

        account_map[account_id] = prepared_account

    return account_map


# ============================================================
# TRANSACTION NORMALIZATION
# ============================================================

def prepare_transactions(transactions, accounts):
    """
    Adapt existing MySQL transaction records to the input
    contract required by the reconciliation engines.

    MySQL fields:
        transaction_id
        user_id
        account_id
        transaction_date
        description
        debit
        credit
        balance

    Added fields:
        date
        currency

    SQL NULL debit/credit values become Decimal("0.00").
    Original records are not modified.
    """

    print("\n[3/4] Normalizing reconciliation inputs...")

    account_currency = {}

    for account in accounts:

        account_id = account.get("account_id")

        if account_id is None:
            continue

        currency = account.get("currency")

        account_currency[account_id] = (
            str(currency).strip().upper()
            if currency
            else None
        )

    prepared = []

    invalid_records = []
    missing_account_currency = 0

    for index, original in enumerate(transactions):

        if not isinstance(original, dict):
            invalid_records.append({
                "row": index,
                "reason": "not_a_dictionary",
            })
            continue

        tx = dict(original)

        # Required date alias.
        if tx.get("date") is None:
            tx["date"] = tx.get("transaction_date")

        # Normalize nullable MySQL financial fields.
        try:
            tx["debit"] = to_decimal(
                tx.get("debit"),
                "debit",
            )

            tx["credit"] = to_decimal(
                tx.get("credit"),
                "credit",
            )

        except ValueError as error:
            invalid_records.append({
                "transaction_id": tx.get("transaction_id"),
                "reason": str(error),
            })
            continue

        # Add currency from the linked account.
        account_id = tx.get("account_id")

        currency = account_currency.get(account_id)

        if currency is not None:
            tx["currency"] = currency
        else:
            tx["currency"] = None
            missing_account_currency += 1

        # Preserve the database transaction ID.
        if tx.get("transaction_id") is None:
            invalid_records.append({
                "row": index,
                "reason": "missing_transaction_id",
            })
            continue

        prepared.append(tx)

    print("Original transaction count:", len(transactions))
    print("Prepared transaction count:", len(prepared))
    print("Invalid records:", len(invalid_records))
    print("Missing account currency:", missing_account_currency)

    return prepared, invalid_records


# ============================================================
# INPUT DIAGNOSTICS
# ============================================================

def print_input_diagnostics(transactions):

    print("\n" + "=" * 65)
    print("RECONCILIATION INPUT DIAGNOSTICS")
    print("=" * 65)

    print("Total transactions:", len(transactions))

    if not transactions:
        return

    fields = [
        "transaction_id",
        "user_id",
        "account_id",
        "date",
        "description",
        "debit",
        "credit",
        "currency",
    ]

    for field in fields:

        available = sum(
            1
            for tx in transactions
            if tx.get(field) is not None
        )

        print(
            f"{field:22}: {available}/{len(transactions)}"
        )

    print("\nSample normalized transaction:")

    print(
        json.dumps(
            transactions[0],
            indent=2,
            default=str,
        )
    )


# ============================================================
# RECONCILIATION EXECUTION
# ============================================================

def run_reconciliation(
    transactions,
    accounts,
    opening_balance=None,
    closing_balance=None,
):

    print("\n[4/4] Running unified reconciliation...")

    kwargs = {
        "accounts": accounts,
        "max_transfer_date_gap_days": TRANSFER_DATE_GAP_DAYS,
        "max_refund_date_gap_days": REFUND_DATE_GAP_DAYS,
        "max_settlement_date_gap_days": SETTLEMENT_DATE_GAP_DAYS,
    }

    # Only run balance reconciliation when both values
    # have explicitly been supplied for this statement.
    if (
        opening_balance is not None
        and closing_balance is not None
    ):
        kwargs["opening_balance"] = opening_balance
        kwargs["closing_balance"] = closing_balance

    result = reconcile_all_transactions(
        transactions,
        **kwargs,
    )

    if not isinstance(result, dict):
        raise RuntimeError(
            "Unified reconciliation returned an invalid response."
        )

    return result


# ============================================================
# REPORTING
# ============================================================

def print_report(result, invalid_records):

    print("\n" + "=" * 75)
    print("FINWELL AI - UNIFIED RECONCILIATION REPORT")
    print("=" * 75)

    print("\nOVERALL STATUS")

    print("Success:", result.get("success"))
    print("Mode:", result.get("mode"))
    print("Writes performed:", result.get("writes_performed"))
    print("Message:", result.get("message"))

    print("\nSUMMARY")

    print(
        json.dumps(
            result.get("summary", {}),
            indent=2,
            default=str,
        )
    )

    print("\nENGINE RESULTS")

    engines = result.get("engines", {})

    for engine_name, engine_result in engines.items():

        print("\n" + "-" * 65)
        print(engine_name.upper())
        print("-" * 65)

        print(
            json.dumps(
                engine_result,
                indent=2,
                default=str,
            )
        )

    print("\nFAILED ENGINES")

    print(
        json.dumps(
            result.get("failed_engines", []),
            indent=2,
        )
    )

    print("\nEXCEPTIONS")

    print(
        json.dumps(
            result.get("exceptions", []),
            indent=2,
            default=str,
        )
    )

    if invalid_records:

        print("\nNORMALIZATION ISSUES")

        print(
            json.dumps(
                invalid_records,
                indent=2,
                default=str,
            )
        )

    # Safety assertion.
    if result.get("writes_performed") is not False:
        raise RuntimeError(
            "Safety check failed: unexpected database write status."
        )

    print("\n" + "=" * 75)
    print("READ-ONLY RECONCILIATION COMPLETED")
    print("No transactions or reconciliation cases were modified.")
    print("=" * 75)


# ============================================================
# MAIN
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description="FinWell AI unified MySQL reconciliation dry run."
    )

    parser.add_argument(
        "--user-id",
        type=int,
        required=True,
        help="Internal MySQL user ID.",
    )

    parser.add_argument(
        "--opening-balance",
        type=str,
        default=None,
        help="Optional statement opening balance.",
    )

    parser.add_argument(
        "--closing-balance",
        type=str,
        default=None,
        help="Optional statement closing balance.",
    )

    args = parser.parse_args()

    try:

        user_id = validate_user_id(args.user_id)

        opening_balance = (
            to_decimal(args.opening_balance, "opening_balance")
            if args.opening_balance is not None
            else None
        )

        closing_balance = (
            to_decimal(args.closing_balance, "closing_balance")
            if args.closing_balance is not None
            else None
        )

        if (
            (opening_balance is None)
            != (closing_balance is None)
        ):
            raise ValueError(
                "Supply both opening and closing balances, or neither."
            )

        print("\nFINWELL AI - UNIFIED RECONCILIATION")
        print("=" * 65)
        print("User ID:", user_id)
        print("Execution mode: READ-ONLY DRY RUN")

        # 1. Retrieve database records.
        raw_transactions = load_transactions(user_id)

        if not raw_transactions:
            print("\nNo transactions found.")
            return 0

        raw_accounts = load_accounts(user_id)

        # 2. Normalize account and transaction inputs.
        account_map = prepare_accounts(raw_accounts)

        transactions, invalid_records = prepare_transactions(
            raw_transactions,
            raw_accounts,
        )

        if not transactions:
            raise RuntimeError(
                "No valid transactions remain after normalization."
            )

        # 3. Show the actual input contract.
        print_input_diagnostics(transactions)

        # 4. Run existing reconciliation engines.
        result = run_reconciliation(
            transactions=transactions,
            accounts=account_map,
            opening_balance=opening_balance,
            closing_balance=closing_balance,
        )

        # 5. Print complete report.
        print_report(result, invalid_records)

        # 6. Save report locally only.
        report_path = "unified_reconciliation_report.json"

        with open(
            report_path,
            "w",
            encoding="utf-8",
        ) as report_file:

            json.dump(
                {
                    "user_id": user_id,
                    "result": result,
                    "normalization_issues": invalid_records,
                },
                report_file,
                indent=4,
                ensure_ascii=False,
                default=str,
            )

        print("\nReport saved locally:", report_path)

        return 0

    except Exception as error:

        print("\nRECONCILIATION ERROR")
        print(type(error).__name__ + ":", error)

        return 1


if __name__ == "__main__":
    sys.exit(main())
