
from mysql.connector import Error
from mysql_pipeline.db import get_db_connection


def save_merchant_mapping(
    user_id,
    original_description,
    normalized_merchant,
    category=None
):
    """
    Save or update a user-specific merchant mapping.
    """

    if not user_id:
        return {
            "success": False,
            "message": "A valid user_id is required."
        }

    if not original_description or not original_description.strip():
        return {
            "success": False,
            "message": "Original description is required."
        }

    if not normalized_merchant or not normalized_merchant.strip():
        return {
            "success": False,
            "message": "Normalized merchant is required."
        }

    connection = None
    cursor = None

    try:
        connection = get_db_connection()

        if connection is None:
            return {
                "success": False,
                "message": "Could not connect to MySQL."
            }

        cursor = connection.cursor()

        query = """
            INSERT INTO merchant_mappings (
                user_id,
                original_description,
                normalized_merchant,
                category
            )
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                normalized_merchant = VALUES(normalized_merchant),
                category = VALUES(category)
        """

        cursor.execute(
            query,
            (
                user_id,
                original_description.strip(),
                normalized_merchant.strip(),
                category
            )
        )

        connection.commit()

        return {
            "success": True,
            "message": "Merchant mapping saved successfully."
        }

    except Error as error:
        if connection:
            connection.rollback()

        return {
            "success": False,
            "message": f"MySQL error: {error}"
        }

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()
