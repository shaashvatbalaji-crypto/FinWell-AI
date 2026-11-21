import pymupdf
import mysql.connector
from mysql_pipeline.db import get_db_connection

connection = get_db_connection()
cursor = connection.cursor(dictionary=True)

cursor.execute("""
    SELECT document_id, file_path
    FROM documents
    WHERE user_id = 1
      AND document_id IN (5, 6, 9, 12)
    ORDER BY document_id
""")

documents = cursor.fetchall()

for document in documents:
    print("\n" + "=" * 70)
    print("DOCUMENT ID:", document["document_id"])
    print("=" * 70)

    try:
        pdf = pymupdf.open(document["file_path"])

        if len(pdf) > 0:
            print(pdf[0].get_text()[:2500])
        else:
            print("PDF contains no pages.")

        pdf.close()

    except Exception as error:
        print("PDF ERROR:", error)

cursor.close()
connection.close()
