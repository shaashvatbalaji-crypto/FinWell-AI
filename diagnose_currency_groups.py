from mysql_pipeline.db import get_db_connection
import json

connection = get_db_connection()
cursor = connection.cursor(dictionary=True)

query = """
SELECT
    COALESCE(a.currency, 'UNKNOWN') AS currency,
    CASE
        WHEN t.account_id IS NULL THEN 'NO_ACCOUNT_ID'
        WHEN a.account_id IS NULL THEN 'ACCOUNT_NOT_FOUND'
        WHEN a.currency IS NULL THEN 'ACCOUNT_CURRENCY_MISSING'
        ELSE 'ACCOUNT_LINKED'
    END AS account_status,
    COUNT(*) AS transaction_count,
    SUM(COALESCE(t.credit, 0)) AS total_credits,
    SUM(COALESCE(t.debit, 0)) AS total_debits
FROM transactions t
INNER JOIN documents d
    ON d.document_id = t.document_id
   AND d.user_id = t.user_id
LEFT JOIN accounts a
    ON a.account_id = t.account_id
   AND a.user_id = t.user_id
WHERE t.user_id = %s
  AND d.processing_status = 'completed'
GROUP BY
    COALESCE(a.currency, 'UNKNOWN'),
    account_status
ORDER BY currency, account_status
"""

cursor.execute(query, (1,))
print(json.dumps(cursor.fetchall(), indent=2, default=str))

cursor.close()
connection.close()
