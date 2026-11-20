
"""
FinWell AI - Multi Account Reconciler

Consolidates transactions across a user's accounts.

Features:
- Account-wise debit and credit totals.
- Internal transfer elimination.
- Consolidated external income and expenses.
- Latest available account balances.
- Estimated opening balances.
- Unmatched and ambiguous transfer reporting.

Input transaction format:
{
    "transaction_id": 101,        # Optional
    "account_id": 1,              # Required
    "date": "2026-12-01",
    "description": "UPI TRANSFER TRF601",
    "debit": 10000.00,
    "credit": None,
    "balance": 50000.00,
    "currency": "INR"             # Optional; defaults to INR
}
"""

from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from reconciliation.inter_account_reconciler import (
    match_inter_account_transfers,
)


def _decimal(value):
    if value is None or value == "":
        return Decimal("0.00")

    try:
        amount = Decimal(
            str(value).replace(",", "").replace("₹", "").strip()
        )

        if not amount.is_finite():
            raise ValueError("Amount must be finite.")

        return amount.quantize(Decimal("0.01"))

    except (InvalidOperation, ValueError):
        raise ValueError(f"Invalid amount: {value!r}")


def _transaction_date(transaction):
    value = (
        transaction.get("date")
        or transaction.get("transaction_date")
    )

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    if value is None:
        return None

    text = str(value).strip()

    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue

    return None


def _money(value):
    return round(float(value), 2)


def reconcile_multiple_accounts(
    transactions,
    accounts=None,
    date_tolerance_days=2,
):
    """
    Consolidate multiple accounts belonging to one user.

    Args:
        transactions:
            Combined list of transactions from all accounts.

        accounts:
            Optional list of account metadata dictionaries:
            {
                "account_id": 1,
                "account_name": "Savings Account",
                "institution_name": "Example Bank",
                "currency": "INR"
            }

        date_tolerance_days:
            Date tolerance passed to the transfer matcher.

    Returns:
        Dictionary containing account-wise and consolidated reports.
    """

    if not isinstance(transactions, list):
        raise TypeError("transactions must be a list.")

    if accounts is None:
        accounts = []

    if not isinstance(accounts, list):
        raise TypeError("accounts must be a list.")

    account_metadata = {
        account["account_id"]: account
        for account in accounts
        if isinstance(account, dict)
        and account.get("account_id") is not None
    }

    # Validate and prepare transactions.
    grouped = defaultdict(list)

    for index, transaction in enumerate(transactions):
        if not isinstance(transaction, dict):
            raise ValueError(
                f"Transaction at index {index} must be a dictionary."
            )

        account_id = transaction.get("account_id")

        if account_id is None:
            raise ValueError(
                f"Transaction at index {index} has no account_id."
            )

        transaction_date = _transaction_date(transaction)

        if transaction_date is None:
            raise ValueError(
                f"Transaction at index {index} has an invalid date."
            )

        debit = _decimal(transaction.get("debit"))
        credit = _decimal(transaction.get("credit"))
        balance = (
            None
            if transaction.get("balance") is None
            else _decimal(transaction.get("balance"))
        )

        if debit < 0 or credit < 0:
            raise ValueError(
                f"Transaction at index {index} has a negative debit/credit."
            )

        if debit > 0 and credit > 0:
            raise ValueError(
                f"Transaction at index {index} has both debit and credit."
            )

        currency = str(
            transaction.get("currency")
            or account_metadata.get(account_id, {}).get("currency")
            or "INR"
        ).upper()

        grouped[account_id].append({
            "original": transaction,
            "date": transaction_date,
            "debit": debit,
            "credit": credit,
            "balance": balance,
            "currency": currency,
            "index": index,
        })

    # Match transfers before calculating external totals.
    transfer_result = match_inter_account_transfers(
        transactions,
        date_tolerance_days=date_tolerance_days,
    )

    # Use Python object identity so duplicate transaction IDs
    # cannot accidentally exclude unrelated records.
    internal_transaction_objects = set()

    for match in transfer_result["matches"]:
        internal_transaction_objects.add(
            id(match["debit_transaction"])
        )
        internal_transaction_objects.add(
            id(match["credit_transaction"])
        )

    account_reports = []
    consolidated = defaultdict(
        lambda: {
            "external_income": Decimal("0.00"),
            "external_expenses": Decimal("0.00"),
            "internal_transfer_debits": Decimal("0.00"),
            "internal_transfer_credits": Decimal("0.00"),
            "closing_balance": Decimal("0.00"),
            "opening_balance_estimate": Decimal("0.00"),
            "accounts_with_balance": 0,
            "accounts_with_opening_estimate": 0,
        }
    )

    for account_id, rows in grouped.items():
        rows.sort(
            key=lambda row: (
                row["date"],
                row["index"],
            )
        )

        currency = rows[0]["currency"]

        if any(row["currency"] != currency for row in rows):
            raise ValueError(
                f"Account {account_id} contains mixed currencies. "
                "Separate the account transactions by currency."
            )

        total_debits = Decimal("0.00")
        total_credits = Decimal("0.00")
        external_income = Decimal("0.00")
        external_expenses = Decimal("0.00")
        internal_debits = Decimal("0.00")
        internal_credits = Decimal("0.00")

        for row in rows:
            total_debits += row["debit"]
            total_credits += row["credit"]

            is_internal = (
                id(row["original"]) in internal_transaction_objects
            )

            if is_internal:
                internal_debits += row["debit"]
                internal_credits += row["credit"]
            else:
                external_expenses += row["debit"]
                external_income += row["credit"]

        # The latest dated transaction balance is the available
        # closing balance for this account.
        rows_with_balance = [
            row for row in rows
            if row["balance"] is not None
        ]

        closing_balance = (
            rows_with_balance[-1]["balance"]
            if rows_with_balance
            else None
        )

        # Estimate opening balance from the earliest transaction:
        # opening = running balance - credit + debit.
        first_row = rows[0]

        opening_balance_estimate = None

        if first_row["balance"] is not None:
            opening_balance_estimate = (
                first_row["balance"]
                - first_row["credit"]
                + first_row["debit"]
            )

        metadata = account_metadata.get(account_id, {})

        account_report = {
            "account_id": account_id,
            "account_name": metadata.get(
                "account_name",
                f"Account {account_id}",
            ),
            "institution_name": metadata.get("institution_name"),
            "currency": currency,
            "transaction_count": len(rows),
            "total_debits": _money(total_debits),
            "total_credits": _money(total_credits),
            "external_income": _money(external_income),
            "external_expenses": _money(external_expenses),
            "internal_transfer_debits": _money(internal_debits),
            "internal_transfer_credits": _money(internal_credits),
            "net_external_cash_flow": _money(
                external_income - external_expenses
            ),
            "closing_balance": (
                _money(closing_balance)
                if closing_balance is not None
                else None
            ),
            "opening_balance_estimate": (
                _money(opening_balance_estimate)
                if opening_balance_estimate is not None
                else None
            ),
        }

        account_reports.append(account_report)

        totals = consolidated[currency]

        totals["external_income"] += external_income
        totals["external_expenses"] += external_expenses
        totals["internal_transfer_debits"] += internal_debits
        totals["internal_transfer_credits"] += internal_credits

        if closing_balance is not None:
            totals["closing_balance"] += closing_balance
            totals["accounts_with_balance"] += 1

        if opening_balance_estimate is not None:
            totals["opening_balance_estimate"] += (
                opening_balance_estimate
            )
            totals["accounts_with_opening_estimate"] += 1

    consolidated_report = {}

    for currency, totals in consolidated.items():
        consolidated_report[currency] = {
            "currency": currency,
            "external_income": _money(totals["external_income"]),
            "external_expenses": _money(
                totals["external_expenses"]
            ),
            "net_external_cash_flow": _money(
                totals["external_income"]
                - totals["external_expenses"]
            ),
            "internal_transfer_debits": _money(
                totals["internal_transfer_debits"]
            ),
            "internal_transfer_credits": _money(
                totals["internal_transfer_credits"]
            ),
            "closing_balance": _money(totals["closing_balance"]),
            "opening_balance_estimate": _money(
                totals["opening_balance_estimate"]
            ),
            "accounts_with_balance": totals["accounts_with_balance"],
            "accounts_with_opening_estimate": (
                totals["accounts_with_opening_estimate"]
            ),
            "account_count": sum(
                1
                for report in account_reports
                if report["currency"] == currency
            ),
        }

    return {
        "success": True,
        "summary": {
            "total_accounts": len(grouped),
            "total_transactions": len(transactions),
            "matched_internal_transfer_pairs": len(
                transfer_result["matches"]
            ),
            "unmatched_transfer_candidates": len(
                transfer_result["ambiguous_transactions"]
            ),
            "currencies": list(consolidated_report.keys()),
        },
        "account_reports": account_reports,
        "consolidated_report": consolidated_report,
        "transfer_reconciliation": transfer_result,
    }
