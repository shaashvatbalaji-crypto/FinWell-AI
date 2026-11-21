from mysql_pipeline.db import get_db_connection
import json

connection = get_db_connection()
cursor = connection.cursor(dictionary=True)

query = """
SELECT
    d.document_id,
    d.original_filename,
    d.document_type,
    d.account_id AS document_account_id,
    a.account_name,
    a.currency,
    COUNT(t.transaction_id) AS transaction_count,
    SUM(t.account_id IS NULL) AS transactions_without_account
FROM documents d
LEFT JOIN accounts a
    ON a.account_id = d.account_id
   AND a.user_id = d.user_id
LEFT JOIN transactions t
    ON t.document_id = d.document_id
   AND t.user_id = d.user_id
WHERE d.user_id = %s
  AND d.processing_status = 'completed'
GROUP BY
    d.document_id,
    d.original_filename,
    d.document_type,
    d.account_id,
    a.account_name,
    a.currency
ORDER BY d.document_id
"""

cursor.execute(query, (1,))
print(json.dumps(cursor.fetchall(), indent=2, default=str))

cursor.close()
connection.close()
