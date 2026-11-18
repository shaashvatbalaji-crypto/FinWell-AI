
from mysql.connector import Error

from mysql_pipeline.db import get_db_connection


def _execute_read_query(query, values):
    """Execute a read-only query and return dictionary rows."""

    connection = None
    cursor = None

    try:
        connection = get_db_connection()

        if connection is None:
            raise RuntimeError("Could not connect to MySQL.")

        cursor = connection.cursor(dictionary=True)
        cursor.execute(query, values)
        rows = cursor.fetchall()

        return {
            "success": True,
            "data": rows,
        }

    except (Error, RuntimeError) as error:
        return {
            "success": False,
            "message": str(error),
            "data": [],
        }

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()


def get_financial_summary(user_id: int):
    """
    Get total income, expenses, net cash flow and transaction count.
    Results are separated by currency.
    Only completed documents are included.
    """

    query = """
        SELECT
            COALESCE(SUM(t.credit), 0) AS total_income,
            COALESCE(SUM(t.debit), 0) AS total_expenses,
            COALESCE(SUM(t.credit), 0)
                - COALESCE(SUM(t.debit), 0) AS net_cash_flow,
            COUNT(*) AS transaction_count,
            COALESCE(a.currency, 'UNKNOWN') AS currency
        FROM transactions t
        INNER JOIN documents d
            ON d.document_id = t.document_id
           AND d.user_id = t.user_id
        LEFT JOIN accounts a
            ON a.account_id = t.account_id
           AND a.user_id = t.user_id
        WHERE t.user_id = %s
          AND d.processing_status = 'completed'
        GROUP BY COALESCE(a.currency, 'UNKNOWN')
        ORDER BY currency
    """

    result = _execute_read_query(query, (user_id,))

    return {
        "success": result["success"],
        "summary": result["data"],
        **({"message": result["message"]} if not result["success"] else {}),
    }


def get_monthly_trends(user_id: int):
    """
    Get monthly income and expense trends.
    Results are separated by currency.
    """

    query = """
        SELECT
            DATE_FORMAT(t.transaction_date, '%Y-%m') AS month,
            COALESCE(SUM(t.credit), 0) AS total_income,
            COALESCE(SUM(t.debit), 0) AS total_expenses,
            COALESCE(SUM(t.credit), 0)
                - COALESCE(SUM(t.debit), 0) AS net_cash_flow,
            COUNT(*) AS transaction_count,
            COALESCE(a.currency, 'UNKNOWN') AS currency
        FROM transactions t
        INNER JOIN documents d
            ON d.document_id = t.document_id
           AND d.user_id = t.user_id
        LEFT JOIN accounts a
            ON a.account_id = t.account_id
           AND a.user_id = t.user_id
        WHERE t.user_id = %s
          AND d.processing_status = 'completed'
        GROUP BY
            DATE_FORMAT(t.transaction_date, '%Y-%m'),
            COALESCE(a.currency, 'UNKNOWN')
        ORDER BY month ASC, currency ASC
    """

    result = _execute_read_query(query, (user_id,))

    return {
        "success": result["success"],
        "monthly_trends": result["data"],
        **({"message": result["message"]} if not result["success"] else {}),
    }


def get_latest_account_balances(user_id: int):
    """
    Get the latest recorded statement balance for each account.

    The latest transaction is selected by transaction_date,
    then transaction_id for ties.

    These are statement balances, not live bank balances.
    """

    query = """
        WITH ranked_transactions AS (
            SELECT
                t.account_id,
                t.balance,
                t.transaction_date,
                t.transaction_id,
                ROW_NUMBER() OVER (
                    PARTITION BY t.account_id
                    ORDER BY
                        t.transaction_date DESC,
                        t.transaction_id DESC
                ) AS row_num
            FROM transactions t
            INNER JOIN documents d
                ON d.document_id = t.document_id
               AND d.user_id = t.user_id
            WHERE t.user_id = %s
              AND t.account_id IS NOT NULL
              AND d.processing_status = 'completed'
        )
        SELECT
            a.account_id,
            a.account_name,
            a.institution_name,
            a.account_type,
            a.currency,
            rt.balance AS latest_recorded_balance,
            rt.transaction_date AS balance_date
        FROM accounts a
        LEFT JOIN ranked_transactions rt
            ON rt.account_id = a.account_id
           AND rt.row_num = 1
        WHERE a.user_id = %s
        ORDER BY a.created_at DESC
    """

    result = _execute_read_query(query, (user_id, user_id))

    return {
        "success": result["success"],
        "account_balances": result["data"],
        **({"message": result["message"]} if not result["success"] else {}),
    }


def get_unlinked_transaction_summary(user_id: int):
    """
    Summarize transactions that do not have an account_id.

    These are kept separate from account-linked transactions.
    """

    query = """
        SELECT
            COALESCE(SUM(t.credit), 0) AS total_income,
            COALESCE(SUM(t.debit), 0) AS total_expenses,
            COALESCE(SUM(t.credit), 0)
                - COALESCE(SUM(t.debit), 0) AS net_cash_flow,
            COUNT(*) AS transaction_count,
            COALESCE(a.currency, 'UNKNOWN') AS currency
        FROM transactions t
        INNER JOIN documents d
            ON d.document_id = t.document_id
           AND d.user_id = t.user_id
        LEFT JOIN accounts a
            ON a.account_id = t.account_id
           AND a.user_id = t.user_id
        WHERE t.user_id = %s
          AND t.account_id IS NULL
          AND d.processing_status = 'completed'
        GROUP BY COALESCE(a.currency, 'UNKNOWN')
        ORDER BY currency
    """

    result = _execute_read_query(query, (user_id,))

    return {
        "success": result["success"],
        "unlinked_summary": result["data"],
        **({"message": result["message"]} if not result["success"] else {}),
    }
