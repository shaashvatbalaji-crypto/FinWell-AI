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