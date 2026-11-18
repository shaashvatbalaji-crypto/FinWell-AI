
from mysql.connector import Error

from mysql_pipeline.db import get_db_connection


def create_user(username: str, email: str, password_hash: str):
    """Create a new user with a securely hashed password."""

    connection = None
    cursor = None

    try:
        connection = get_db_connection()

        if connection is None:
            return {
                "success": False,
                "message": "Database connection failed."
            }

        cursor = connection.cursor()

        query = """
            INSERT INTO users (username, email, password_hash)
            VALUES (%s, %s, %s)
        """

        cursor.execute(query, (username, email, password_hash))
        connection.commit()

        return {
            "success": True,
            "user_id": cursor.lastrowid,
            "username": username,
            "email": email
        }

    except Error as error:
        if connection is not None:
            connection.rollback()

        if error.errno == 1062:
            return {
                "success": False,
                "message": "Username or email already exists."
            }

        return {
            "success": False,
            "message": "Unable to create user."
        }

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()


def get_user_by_email(email: str):
    """Retrieve a user using their email address."""

    connection = None
    cursor = None

    try:
        connection = get_db_connection()

        if connection is None:
            return None

        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT user_id, username, email, password_hash
            FROM users
            WHERE email = %s
            """,
            (email,)
        )

        return cursor.fetchone()

    except Error:
        return None

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()
