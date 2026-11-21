import pymupdf
from mysql_pipeline.db import get_db_connection

connection = get_db_connection()
cursor = connection.cursor(dictionary=True)

cursor.execute("""
    SELECT document_id, file_path
    FROM documents
    WHERE user_id = 1
      AND document_id IN (14, 15)
    ORDER BY document_id
""")

for document in cursor.fetchall():
    print("\n" + "=" * 65)
    print("DOCUMENT:", document["document_id"])
    print("=" * 65)

    pdf = pymupdf.open(document["file_path"])
    print(pdf[0].get_text()[:1800])
    pdf.close()

cursor.close()
connection.close()
