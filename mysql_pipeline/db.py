import mysql.connector
from mysql.connector import Error

from config.settings import (
    MYSQL_HOST,
    MYSQL_PORT,
    MYSQL_USER,
    MYSQL_PASSWORD,
    MYSQL_DATABASE,
)


def get_db_connection():
    """Connect to the FinWell AI MySQL database."""

    try:
        connection = mysql.connector.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE,
            connection_timeout=10,
        )

        if connection.is_connected():
            return connection

        return None

    except Error as error:
        print(f"MySQL connection failed: {error}")
        return None


def test_db_connection():
    """Test the connection using a simple query."""

    connection = None

    try:
        connection = get_db_connection()

        if connection is None:
            return {
                "success": False,
                "message": "Could not connect to MySQL."
            }

        cursor = connection.cursor()
        cursor.execute("SELECT DATABASE(), VERSION()")
        database_name, mysql_version = cursor.fetchone()
        cursor.close()

        return {
            "success": True,
            "message": "Successfully connected to MySQL.",
            "database": database_name,
            "mysql_version": mysql_version,
        }

    except Error as error:
        return {
            "success": False,
            "message": str(error)
        }

    finally:
        if connection is not None and connection.is_connected():
            connection.close()