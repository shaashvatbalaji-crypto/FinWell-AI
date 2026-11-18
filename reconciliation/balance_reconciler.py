
from decimal import Decimal, InvalidOperation


ZERO = Decimal("0.00")


def _amount(value, field_name, allow_none=True):
    if value is None:
        if allow_none:
            return ZERO
        raise ValueError(f"{field_name} is required.")

    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be numeric.")

    try:
        amount = Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError(f"{field_name} must be numeric.")

    if not amount.is_finite():
        raise ValueError(f"{field_name} must be finite.")

    return amount.quantize(Decimal("0.01"))


def reconcile_statement_balance(
    transactions,
    opening_balance,
    closing_balance,
    tolerance=Decimal("0.01"),
    check_running_balance=True,
):
    """
    Reconcile statement-level and optional transaction-level balances.

    Transactions must be supplied in statement order.

    Expected transaction fields:
        debit
        credit
        balance (optional, for running balance checks)

    This function is read-only and performs no database or ChromaDB writes.
    """

    result = {
        "success": True,
        "mode": "dry_run",
        "writes_performed": False,
        "transaction_count": len(transactions) if isinstance(transactions, list) else 0,
        "valid_transaction_count": 0,
        "invalid_transaction_count": 0,
        "total_debits": ZERO,
        "total_credits": ZERO,
        "opening_balance": None,
        "expected_closing_balance": None,
        "actual_closing_balance": None,
        "difference": None,
        "statement_balanced": False,
        "running_balance_checked": False,
        "running_balance_mismatches": [],
        "invalid_transactions": [],
        "message": None,
    }

    if not isinstance(transactions, list):
        result["success"] = False
        result["message"] = "Transactions must be provided as a list."
        return result

    try:
        opening = _amount(opening_balance, "opening_balance", False)
        closing = _amount(closing_balance, "closing_balance", False)
        allowed_difference = _amount(tolerance, "tolerance", False)

        if allowed_difference < ZERO:
            raise ValueError("Tolerance cannot be negative.")

    except ValueError as error:
        result["success"] = False
        result["message"] = str(error)
        return result

    result["opening_balance"] = opening
    result["actual_closing_balance"] = closing

    valid_transactions = []

    for index, transaction in enumerate(transactions):

        if not isinstance(transaction, dict):
            result["invalid_transactions"].append({
                "index": index,
                "reason": "Transaction must be a dictionary.",
            })
            continue

        try:
            debit = _amount(transaction.get("debit"), "debit")
            credit = _amount(transaction.get("credit"), "credit")

            if debit < ZERO or credit < ZERO:
                raise ValueError("Debit and credit cannot be negative.")

            if debit > ZERO and credit > ZERO:
                raise ValueError(
                    "Debit and credit cannot both be positive."
                )

            balance_value = transaction.get("balance")
            balance = (
                _amount(balance_value, "balance")
                if balance_value is not None
                else None
            )

            valid_transactions.append({
                "index": index,
                "debit": debit,
                "credit": credit,
                "balance": balance,
            })

        except ValueError as error:
            result["invalid_transactions"].append({
                "index": index,
                "transaction_id": transaction.get("transaction_id"),
                "reason": str(error),
            })

    result["valid_transaction_count"] = len(valid_transactions)
    result["invalid_transaction_count"] = len(
        result["invalid_transactions"]
    )

    total_debits = sum(
        (item["debit"] for item in valid_transactions),
        ZERO,
    )

    total_credits = sum(
        (item["credit"] for item in valid_transactions),
        ZERO,
    )

    expected_closing = opening + total_credits - total_debits
    difference = closing - expected_closing

    result["total_debits"] = total_debits
    result["total_credits"] = total_credits
    result["expected_closing_balance"] = expected_closing
    result["difference"] = difference

    result["statement_balanced"] = (
        abs(difference) <= allowed_difference
        and not result["invalid_transactions"]
    )

    # Optional running balance validation.
    if check_running_balance:
        result["running_balance_checked"] = True

        running_balance = opening

        for item in valid_transactions:
            running_balance += item["credit"] - item["debit"]

            actual_balance = item["balance"]

            if actual_balance is None:
                continue

            row_difference = actual_balance - running_balance

            if abs(row_difference) > allowed_difference:
                result["running_balance_mismatches"].append({
                    "transaction_index": item["index"],
                    "expected_balance": running_balance,
                    "actual_balance": actual_balance,
                    "difference": row_difference,
                })

    if result["invalid_transactions"]:
        result["message"] = (
            "Balance analysis is incomplete because some transactions "
            "are invalid."
        )

    elif not result["statement_balanced"]:
        result["message"] = (
            "Statement closing balance does not match the calculated balance."
        )

    elif result["running_balance_mismatches"]:
        result["message"] = (
            "Statement totals balance, but running balance discrepancies exist."
        )

    else:
        result["message"] = (
            "Statement balance reconciliation passed."
        )

    return result
