from mysql.connector import Error
from mysql_pipeline.db import get_db_connection


def check_duplicate_document(user_id, file_hash):
    """
    Check whether this user has already uploaded a document
    with the same SHA-256 hash.

    This function only detects duplicates. It does not delete
    or modify any document.
    """

    connection = None
    cursor = None

    try:
        connection = get_db_connection()

        if connection is None:
            return {
                "success": False,
                "is_duplicate": False,
                "document_id": None,
                "message": "Could not connect to MySQL.",
            }

        cursor = connection.cursor(dictionary=True)

        query = """
            SELECT document_id, original_filename, uploaded_at
            FROM documents
            WHERE user_id = %s AND file_hash = %s
            ORDER BY uploaded_at DESC
            LIMIT 1
        """

        cursor.execute(query, (user_id, file_hash))
        existing_document = cursor.fetchone()

        if existing_document:
            return {
                "success": True,
                "is_duplicate": True,
                "document_id": existing_document["document_id"],
                "original_filename": existing_document["original_filename"],
                "message": "This document has already been uploaded.",
            }

        return {
            "success": True,
            "is_duplicate": False,
            "document_id": None,
            "original_filename": None,
            "message": "No duplicate document found.",
        }

    except Error as error:
        return {
            "success": False,
            "is_duplicate": False,
            "document_id": None,
            "message": f"MySQL error: {error}",
        }

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()