
from mysql.connector import Error
from mysql_pipeline.db import get_db_connection


def save_investment(
    user_id,
    document_id,
    investment_name=None,
    investment_type=None,
    quantity=None,
    purchase_value=None,
    current_value=None,
    investment_date=None,
):
    """
    Save extracted investment information into the MySQL investments table.
    """

    connection = None
    cursor = None

    try:
        connection = get_db_connection()

        if connection is None:
            return {
                "success": False,
                "message": "Could not connect to MySQL.",
                "investment_id": None,
            }

        cursor = connection.cursor()

        query = """
            INSERT INTO investments (
                user_id,
                document_id,
                investment_name,
                investment_type,
                quantity,
                purchase_value,
                current_value,
                investment_date
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """

        values = (
            user_id,
            document_id,
            investment_name,
            investment_type,
            quantity,
            purchase_value,
            current_value,
            investment_date,
        )

        cursor.execute(query, values)
        connection.commit()

        return {
            "success": True,
            "message": "Investment information saved successfully.",
            "investment_id": cursor.lastrowid,
        }

    except Error as error:
        if connection:
            connection.rollback()

        return {
            "success": False,
            "message": f"MySQL error: {error}",
            "investment_id": None,
        }

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()


def list_user_investments(user_id):
    """
    Retrieve all investment records belonging to a specific user.
    """

    connection = None
    cursor = None

    try:
        if not isinstance(user_id, int) or isinstance(user_id, bool) or user_id <= 0:
            return {
                "success": False,
                "message": "A valid user_id is required.",
                "investments": [],
                "count": 0,
            }

        connection = get_db_connection()

        if connection is None:
            return {
                "success": False,
                "message": "Could not connect to MySQL.",
                "investments": [],
                "count": 0,
            }

        cursor = connection.cursor(dictionary=True)

        query = """
            SELECT
                investment_id,
                user_id,
                document_id,
                investment_name,
                investment_type,
                quantity,
                purchase_value,
                current_value,
                investment_date,
                created_at
            FROM investments
            WHERE user_id = %s
            ORDER BY investment_id DESC
        """

        cursor.execute(query, (user_id,))
        investments = cursor.fetchall()

        return {
            "success": True,
            "message": "Investments retrieved successfully.",
            "investments": investments,
            "count": len(investments),
        }

    except Error as error:
        return {
            "success": False,
            "message": f"MySQL error: {error}",
            "investments": [],
            "count": 0,
        }

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()
