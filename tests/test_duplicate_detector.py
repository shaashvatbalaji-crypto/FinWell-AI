from mysql_pipeline.db import get_db_connection
from mysql_pipeline.duplicate_detector import check_duplicate_document


# Find an existing document to use for this test.
connection = get_db_connection()
cursor = connection.cursor(dictionary=True)

cursor.execute("""
    SELECT user_id, file_hash
    FROM documents
    ORDER BY document_id
    LIMIT 1
""")

existing_document = cursor.fetchone()

cursor.close()
connection.close()


if existing_document is None:
    print("SKIP: No document exists in the database to test against.")
else:
    result = check_duplicate_document(
        user_id=existing_document["user_id"],
        file_hash=existing_document["file_hash"],
    )

    print("Duplicate detection result:", result)

    if result["success"] and result["is_duplicate"]:
        print("PASS: Existing document was detected as a duplicate.")
    else:
        print("FAIL: Existing document was not detected.")