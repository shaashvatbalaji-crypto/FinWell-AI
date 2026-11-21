from mysql_pipeline.db import get_db_connection
import json

connection = get_db_connection()
cursor = connection.cursor(dictionary=True)

print("\n========== DOCUMENT TABLE COLUMNS ==========")
cursor.execute("SHOW COLUMNS FROM documents")
print(json.dumps(cursor.fetchall(), indent=2, default=str))

print("\n========== UNLINKED TRANSACTIONS BY DOCUMENT ==========")
query = """
SELECT
    t.document_id,
    COUNT(*) AS transaction_count,
    MIN(t.transaction_date) AS first_transaction,
    MAX(t.transaction_date) AS last_transaction,
    SUM(COALESCE(t.credit, 0)) AS total_credits,
    SUM(COALESCE(t.debit, 0)) AS total_debits
FROM transactions t
INNER JOIN documents d
    ON d.document_id = t.document_id
   AND d.user_id = t.user_id
WHERE t.user_id = %s
  AND t.account_id IS NULL
  AND d.processing_status = 'completed'
GROUP BY t.document_id
ORDER BY t.document_id
"""

cursor.execute(query, (1,))
print(json.dumps(cursor.fetchall(), indent=2, default=str))

print("\n========== SAMPLE UNLINKED TRANSACTIONS ==========")
query = """
SELECT
    transaction_id,
    document_id,
    transaction_date,
    description,
    debit,
    credit
FROM transactions
WHERE user_id = %s
  AND account_id IS NULL
ORDER BY transaction_date
LIMIT 15
"""

cursor.execute(query, (1,))
print(json.dumps(cursor.fetchall(), indent=2, default=str))

cursor.close()
connection.close()
