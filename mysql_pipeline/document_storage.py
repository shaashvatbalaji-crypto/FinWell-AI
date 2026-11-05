
from mysql.connector import Error

from mysql_pipeline.db import get_db_connection


def save_document(
    user_id: int,
    original_filename: str,
    stored_filename: str,
    file_path: str,
    file_hash: str,
    document_type: str = "unknown",
    page_count: int = 0,
):
    """
    Save a newly uploaded document record in MySQL.

    MySQL automatically generates and returns the document_id.
    """

    connection = None
    cursor = None

    try:
        connection = get_db_connection()

        if connection is None:
            return {
                "success": False,
                "message": "Could not connect to MySQL.",
                "document_id": None,
            }

        cursor = connection.cursor()

        query = """
            INSERT INTO documents (
                user_id,
                original_filename,
                stored_filename,
                file_path,
                file_hash,
                document_type,
                page_count,
                processing_status
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """

        values = (
            user_id,
            original_filename,
            stored_filename,
            file_path,
            file_hash,
            document_type,
            page_count,
            "uploaded",
        )

        cursor.execute(query, values)
        connection.commit()

        return {
            "success": True,
            "message": "Document record saved successfully.",
            "document_id": cursor.lastrowid,
        }

    except Error as error:
        if connection is not None:
            connection.rollback()

        return {
            "success": False,
            "message": str(error),
            "document_id": None,
        }

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()


def get_document_by_id(document_id: int, user_id: int):
    """Retrieve one document belonging to a specific user."""

    connection = None
    cursor = None

    try:
        connection = get_db_connection()

        if connection is None:
            return {
                "success": False,
                "message": "Could not connect to MySQL.",
                "document": None,
            }

        cursor = connection.cursor(dictionary=True)

        query = """
            SELECT
                document_id,
                user_id,
                original_filename,
                stored_filename,
                file_path,
                file_hash,
                document_type,
                page_count,
                processing_status,
                error_message,
                uploaded_at,
                processed_at
            FROM documents
            WHERE document_id = %s AND user_id = %s
        """

        cursor.execute(query, (document_id, user_id))
        document = cursor.fetchone()

        if document is None:
            return {
                "success": False,
                "message": "Document not found for this user.",
                "document": None,
            }

        return {
            "success": True,
            "message": "Document retrieved successfully.",
            "document": document,
        }

    except Error as error:
        return {
            "success": False,
            "message": str(error),
            "document": None,
        }

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()


def list_user_documents(user_id: int):
    """List documents belonging to a specific user."""

    connection = None
    cursor = None

    try:
        connection = get_db_connection()

        if connection is None:
            return {
                "success": False,
                "message": "Could not connect to MySQL.",
                "documents": [],
            }

        cursor = connection.cursor(dictionary=True)

        query = """
            SELECT
                document_id,
                original_filename,
                document_type,
                page_count,
                processing_status,
                uploaded_at,
                processed_at
            FROM documents
            WHERE user_id = %s
            ORDER BY uploaded_at DESC
        """

        cursor.execute(query, (user_id,))
        documents = cursor.fetchall()

        return {
            "success": True,
            "message": "Documents retrieved successfully.",
            "documents": documents,
            "count": len(documents),
        }

    except Error as error:
        return {
            "success": False,
            "message": str(error),
            "documents": [],
        }

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()


def update_document_status(
    document_id: int,
    user_id: int,
    status: str,
    error_message: str = None,
):
    """
    Update a document's processing status for its owner.

    Allowed statuses:
    uploaded, processing, completed, failed
    """

    allowed_statuses = {
        "uploaded",
        "processing",
        "completed",
        "failed",
    }

    if status not in allowed_statuses:
        return {
            "success": False,
            "message": (
                f"Invalid status. Allowed values: "
                f"{sorted(allowed_statuses)}"
            ),
        }

    connection = None
    cursor = None

    try:
        connection = get_db_connection()

        if connection is None:
            return {
                "success": False,
                "message": "Could not connect to MySQL.",
            }

        cursor = connection.cursor()

        query = """
            UPDATE documents
            SET
                processing_status = %s,
                error_message = %s,
                processed_at = CASE
                    WHEN %s IN ('completed', 'failed')
                    THEN CURRENT_TIMESTAMP
                    ELSE NULL
                END
            WHERE document_id = %s
              AND user_id = %s
        """

        values = (
            status,
            error_message,
            status,
            document_id,
            user_id,
        )

        cursor.execute(query, values)
        connection.commit()

        if cursor.rowcount == 0:
            return {
                "success": False,
                "message": (
                    "Document not found for this user, "
                    "or the status was unchanged."
                ),
            }

        return {
            "success": True,
            "message": "Document status updated successfully.",
        }

    except Error as error:
        if connection is not None:
            connection.rollback()

        return {
            "success": False,
            "message": str(error),
        }

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()
def update_document_type(
    document_id: int,
    user_id: int,
    document_type: str,
):
    """Update the detected document type for its owner."""

    allowed_types = {
        "bank_statement",
        "credit_card_statement",
        "loan_agreement",
        "insurance_policy",
        "investment_statement",
        "unknown",
    }

    if document_type not in allowed_types:
        return {
            "success": False,
            "message": f"Invalid document type: {document_type}",
        }

    connection = None
    cursor = None

    try:
        connection = get_db_connection()

        if connection is None:
            return {
                "success": False,
                "message": "Could not connect to MySQL.",
            }

        cursor = connection.cursor()

        query = """
            UPDATE documents
            SET document_type = %s
            WHERE document_id = %s
              AND user_id = %s
        """

        cursor.execute(
            query,
            (document_type, document_id, user_id),
        )

        connection.commit()

        if cursor.rowcount == 0:
            return {
                "success": False,
                "message": "Document not found for this user.",
            }

        return {
            "success": True,
            "message": "Document type updated successfully.",
        }

    except Error as error:
        if connection is not None:
            connection.rollback()

        return {
            "success": False,
            "message": str(error),
        }

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()