
from mysql_pipeline.db import get_db_connection


VALID_ACCOUNT_TYPES = {
    "savings",
    "current",
    "salary",
    "credit_card",
    "loan",
    "investment",
    "cash",
    "other",
}


def create_account(
    user_id,
    account_name,
    institution_name=None,
    account_type="other",
    masked_account_number=None,
    currency="INR",
):
    """Create a financial account for a user."""

    if not isinstance(user_id, int) or user_id <= 0:
        return {
            "success": False,
            "message": "A valid user_id is required.",
        }

    if not isinstance(account_name, str) or not account_name.strip():
        return {
            "success": False,
            "message": "Account name is required.",
        }

    account_name = account_name.strip()
    account_type = str(account_type).strip().lower()
    currency = str(currency).strip().upper()

    if account_type not in VALID_ACCOUNT_TYPES:
        return {
            "success": False,
            "message": "Invalid account type.",
        }

    if len(currency) != 3 or not currency.isalpha():
        return {
            "success": False,
            "message": "Currency must be a 3-letter code, such as INR.",
        }

    connection = None
    cursor = None

    try:
        connection = get_db_connection()

        if connection is None:
            raise RuntimeError("Could not connect to MySQL.")

        cursor = connection.cursor()

        query = """
            INSERT INTO accounts (
                user_id,
                account_name,
                institution_name,
                account_type,
                masked_account_number,
                currency
            )
            VALUES (%s, %s, %s, %s, %s, %s)
        """

        values = (
            user_id,
            account_name,
            institution_name,
            account_type,
            masked_account_number,
            currency,
        )

        cursor.execute(query, values)
        connection.commit()

        return {
            "success": True,
            "account_id": cursor.lastrowid,
            "message": "Account created successfully.",
        }

    except Exception as error:
        if connection:
            connection.rollback()

        return {
            "success": False,
            "message": f"Account creation failed: {error}",
        }

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


def list_user_accounts(user_id):
    """List all accounts belonging to a user."""

    connection = None
    cursor = None

    try:
        connection = get_db_connection()

        if connection is None:
            raise RuntimeError("Could not connect to MySQL.")

        cursor = connection.cursor(dictionary=True)

        query = """
            SELECT
                account_id,
                user_id,
                account_name,
                institution_name,
                account_type,
                masked_account_number,
                currency,
                created_at
            FROM accounts
            WHERE user_id = %s
            ORDER BY created_at DESC
        """

        cursor.execute(query, (user_id,))
        accounts = cursor.fetchall()

        return {
            "success": True,
            "accounts": accounts,
            "total_accounts": len(accounts),
        }

    except Exception as error:
        return {
            "success": False,
            "accounts": [],
            "message": f"Could not retrieve accounts: {error}",
        }

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


def get_account_by_id(user_id, account_id):
    """Retrieve an account only if it belongs to the given user."""

    connection = None
    cursor = None

    try:
        connection = get_db_connection()

        if connection is None:
            raise RuntimeError("Could not connect to MySQL.")

        cursor = connection.cursor(dictionary=True)

        query = """
            SELECT
                account_id,
                user_id,
                account_name,
                institution_name,
                account_type,
                masked_account_number,
                currency,
                created_at
            FROM accounts
            WHERE account_id = %s
              AND user_id = %s
            LIMIT 1
        """

        cursor.execute(query, (account_id, user_id))
        account = cursor.fetchone()

        if not account:
            return {
                "success": False,
                "account": None,
                "message": "Account not found for this user.",
            }

        return {
            "success": True,
            "account": account,
        }

    except Exception as error:
        return {
            "success": False,
            "account": None,
            "message": f"Could not retrieve account: {error}",
        }

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()
