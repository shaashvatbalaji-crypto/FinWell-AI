
from mysql.connector import Error

from mysql_pipeline.db import get_db_connection


def _get_document_account_id(cursor, document_id: int, user_id: int):
    """
    Retrieve the account_id associated with a document.

    Also verifies that the document belongs to the specified user.

    Returns:
        account_id if the document exists.
        None if the document has no associated account.

    Raises:
        ValueError if the document does not belong to the user.
    """

    query = """
        SELECT account_id
        FROM documents
        WHERE document_id = %s
          AND user_id = %s
    """

    cursor.execute(query, (document_id, user_id))
    document = cursor.fetchone()

    if document is None:
        raise ValueError("Document not found for this user.")

    return document[0]


def save_transaction(
    user_id: int,
    document_id: int,
    transaction_date: str,
    description: str,
    debit: float = None,
    credit: float = None,
    balance: float = None,
):
    """
    Save one extracted transaction in MySQL.

    The account_id is automatically inherited from its parent document.
    """

    connection = None
    cursor = None

    try:
        connection = get_db_connection()

        if connection is None:
            return {
                "success": False,
                "message": "Could not connect to MySQL.",
                "transaction_id": None,
            }

        cursor = connection.cursor()

        # Step 1: Verify document ownership and retrieve account_id.
        account_id = _get_document_account_id(
            cursor,
            document_id,
            user_id,
        )

        # Step 2: Insert transaction with inherited account_id.
        query = """
            INSERT INTO transactions (
                user_id,
                document_id,
                account_id,
                transaction_date,
                description,
                debit,
                credit,
                balance
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """

        values = (
            user_id,
            document_id,
            account_id,
            transaction_date,
            description,
            debit,
            credit,
            balance,
        )

        cursor.execute(query, values)
        connection.commit()

        return {
            "success": True,
            "message": "Transaction saved successfully.",
            "transaction_id": cursor.lastrowid,
            "account_id": account_id,
        }

    except (Error, ValueError) as error:

        if connection is not None:
            connection.rollback()

        return {
            "success": False,
            "message": str(error),
            "transaction_id": None,
        }

    finally:

        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()


def save_transactions(
    user_id: int,
    document_id: int,
    transactions: list,
):
    """
    Save multiple validated transactions in MySQL.

    All transactions automatically inherit the account_id
    of their parent document.

    Existing documents with account_id = NULL are supported.
    """

    if not transactions:
        return {
            "success": True,
            "message": "No transactions to save.",
            "saved_count": 0,
        }

    connection = None
    cursor = None

    try:
        connection = get_db_connection()

        if connection is None:
            return {
                "success": False,
                "message": "Could not connect to MySQL.",
                "saved_count": 0,
            }

        cursor = connection.cursor()

        # Step 1: Verify document ownership and retrieve account_id.
        account_id = _get_document_account_id(
            cursor,
            document_id,
            user_id,
        )

        # Step 2: Prepare transaction insertion query.
        query = """
            INSERT INTO transactions (
                user_id,
                document_id,
                account_id,
                transaction_date,
                description,
                debit,
                credit,
                balance
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """

        # The parser/normalizer uses "date".
        # MySQL's column is named "transaction_date".
        values = [
            (
                user_id,
                document_id,
                account_id,
                transaction["date"],
                transaction["description"],
                transaction.get("debit"),
                transaction.get("credit"),
                transaction.get("balance"),
            )
            for transaction in transactions
        ]

        # Step 3: Insert all transactions.
        cursor.executemany(query, values)
        connection.commit()

        return {
            "success": True,
            "message": "Transactions saved successfully.",
            "saved_count": cursor.rowcount,
            "account_id": account_id,
        }

    except (Error, KeyError, TypeError, ValueError) as error:

        if connection is not None:
            connection.rollback()

        return {
            "success": False,
            "message": str(error),
            "saved_count": 0,
        }

    finally:

        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()


def list_document_transactions(
    document_id: int,
    user_id: int,
):
    """
    Retrieve transactions belonging to a specific user's document.

    Includes account_id.
    """

    connection = None
    cursor = None

    try:
        connection = get_db_connection()

        if connection is None:
            return {
                "success": False,
                "message": "Could not connect to MySQL.",
                "transactions": [],
            }

        cursor = connection.cursor(dictionary=True)

        query = """
            SELECT
                transaction_id,
                user_id,
                document_id,
                account_id,
                transaction_date,
                description,
                debit,
                credit,
                balance,
                created_at
            FROM transactions
            WHERE document_id = %s
              AND user_id = %s
            ORDER BY transaction_date ASC, transaction_id ASC
        """

        cursor.execute(query, (document_id, user_id))
        rows = cursor.fetchall()

        return {
            "success": True,
            "message": "Transactions retrieved successfully.",
            "count": len(rows),
            "transactions": rows,
        }

    except Error as error:

        return {
            "success": False,
            "message": str(error),
            "transactions": [],
        }

    finally:

        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()


def list_user_transactions(
    user_id: int,
    limit: int = 100,
    offset: int = 0,
):
    """
    Retrieve a user's transactions with pagination.

    Includes account_id.
    """

    connection = None
    cursor = None

    try:
        connection = get_db_connection()

        if connection is None:
            return {
                "success": False,
                "message": "Could not connect to MySQL.",
                "transactions": [],
            }

        cursor = connection.cursor(dictionary=True)

        query = """
            SELECT
                transaction_id,
                user_id,
                document_id,
                account_id,
                transaction_date,
                description,
                debit,
                credit,
                balance,
                created_at
            FROM transactions
            WHERE user_id = %s
            ORDER BY transaction_date DESC, transaction_id DESC
            LIMIT %s OFFSET %s
        """

        cursor.execute(query, (user_id, limit, offset))
        rows = cursor.fetchall()

        return {
            "success": True,
            "message": "User transactions retrieved successfully.",
            "count": len(rows),
            "transactions": rows,
        }

    except Error as error:

        return {
            "success": False,
            "message": str(error),
            "transactions": [],
        }

    finally:

        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()
