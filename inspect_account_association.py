from mysql_pipeline.db import get_db_connection
import json

connection = get_db_connection()
cursor = connection.cursor(dictionary=True)

print("\n========== USER ACCOUNTS ==========")
cursor.execute("""
    SELECT account_id, account_name, institution_name,
           account_type, currency
    FROM accounts
    WHERE user_id = %s
    ORDER BY account_id
""", (1,))
print(json.dumps(cursor.fetchall(), indent=2, default=str))

print("\n========== DOCUMENT SOURCE DETAILS ==========")
cursor.execute("""
    SELECT document_id, original_filename, stored_filename,
           file_path, document_type, account_id, processing_status
    FROM documents
    WHERE user_id = %s
      AND document_id IN (5, 6, 9, 12, 14, 15)
    ORDER BY document_id
""", (1,))
print(json.dumps(cursor.fetchall(), indent=2, default=str))

cursor.close()
connection.close()
