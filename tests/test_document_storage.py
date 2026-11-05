from mysql_pipeline.db import get_db_connection
from mysql_pipeline.document_storage import save_document


def run_test():
    connection = None
    cursor = None

    try:
        # Create a temporary test user record.
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO users (username, email)
            VALUES (%s, %s)
            """,
            ("finwell_test_user", "finwell_test@example.com"),
        )

        connection.commit()
        test_user_id = cursor.lastrowid

        # Test saving document metadata.
        result = save_document(
            user_id=test_user_id,
            original_filename="sample_statement.pdf",
            stored_filename="test_sample_statement.pdf",
            file_path="data/uploads/test_sample_statement.pdf",
            file_hash="a" * 64,
            document_type="bank_statement",
            page_count=2,
        )

        print("Document storage result:", result)

        if result["success"]:
            print("PASS: Document metadata was saved.")
        else:
            print("FAIL:", result["message"])

    except Exception as error:
        print("Test failed:", error)

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()


if __name__ == "__main__":
    run_test()