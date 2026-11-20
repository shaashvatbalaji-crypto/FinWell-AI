
from mysql.connector import Error
from mysql_pipeline.db import get_db_connection


def save_loan(
    user_id,
    document_id,
    lender_name=None,
    loan_type=None,
    principal_amount=None,
    interest_rate=None,
    loan_start_date=None,
    loan_end_date=None,
    monthly_emi=None,
):
    """
    Save extracted loan information into the MySQL loans table.
    """

    connection = None
    cursor = None

    try:
        connection = get_db_connection()

        if connection is None:
            return {
                "success": False,
                "message": "Could not connect to MySQL.",
                "loan_id": None,
            }

        cursor = connection.cursor()

        query = """
            INSERT INTO loans (
                user_id,
                document_id,
                lender_name,
                loan_type,
                principal_amount,
                interest_rate,
                loan_start_date,
                loan_end_date,
                monthly_emi
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        values = (
            user_id,
            document_id,
            lender_name,
            loan_type,
            principal_amount,
            interest_rate,
            loan_start_date,
            loan_end_date,
            monthly_emi,
        )

        cursor.execute(query, values)
        connection.commit()

        return {
            "success": True,
            "message": "Loan information saved successfully.",
            "loan_id": cursor.lastrowid,
        }

    except Error as error:
        if connection:
            connection.rollback()

        return {
            "success": False,
            "message": f"MySQL error: {error}",
            "loan_id": None,
        }

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()


def list_user_loans(user_id):
    """
    Retrieve all loan records belonging to a specific user.
    """

    connection = None
    cursor = None

    try:
        if not isinstance(user_id, int) or isinstance(user_id, bool) or user_id <= 0:
            return {
                "success": False,
                "message": "A valid user_id is required.",
                "loans": [],
                "count": 0,
            }

        connection = get_db_connection()

        if connection is None:
            return {
                "success": False,
                "message": "Could not connect to MySQL.",
                "loans": [],
                "count": 0,
            }

        cursor = connection.cursor(dictionary=True)

        query = """
            SELECT
                loan_id,
                user_id,
                document_id,
                lender_name,
                loan_type,
                principal_amount,
                interest_rate,
                loan_start_date,
                loan_end_date,
                monthly_emi,
                created_at
            FROM loans
            WHERE user_id = %s
            ORDER BY loan_id DESC
        """

        cursor.execute(query, (user_id,))
        loans = cursor.fetchall()

        return {
            "success": True,
            "message": "Loans retrieved successfully.",
            "loans": loans,
            "count": len(loans),
        }

    except Error as error:
        return {
            "success": False,
            "message": f"MySQL error: {error}",
            "loans": [],
            "count": 0,
        }

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()
