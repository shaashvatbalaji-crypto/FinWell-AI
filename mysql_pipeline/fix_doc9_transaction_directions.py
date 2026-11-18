from pathlib import Path
from decimal import Decimal

from pdf_extraction.pdf_reader import extract_pdf_text
from preprocessing.text_cleaner import clean_extracted_text
from preprocessing.transaction_parser import parse_transactions
from mysql_pipeline.db import get_db_connection


DOCUMENT_ID = 9
PDF_PATH = Path(
    r"C:\Users\shaas\OneDrive\Desktop\FinWell_AI\FinWell_AI\data\uploads\user_1\40109bfd401448e0ba75a134ad17f462.pdf"
)


def money(value):
    if value is None:
        return Decimal("0.00")
    return Decimal(str(value)).quantize(Decimal("0.01"))


def main():
    # 1. Parse the source PDF using the corrected parser
    extracted = extract_pdf_text(str(PDF_PATH))
    cleaned = clean_extracted_text(extracted["full_text"])["cleaned_text"]
    parsed_result = parse_transactions(cleaned)

    if not parsed_result.get("success"):
        raise RuntimeError("Parser reported failure. No database changes made.")

    parsed_rows = parsed_result.get("transactions", [])

    if len(parsed_rows) != 31:
        raise RuntimeError(
            f"Expected 31 parsed transactions, got {len(parsed_rows)}. "
            "No database changes made."
        )

    # Build a unique lookup using date + exact description
    parsed_lookup = {}

    for row in parsed_rows:
        key = (row["date"], row["description"])

        if key in parsed_lookup:
            raise RuntimeError(
                f"Duplicate parsed transaction key: {key}. "
                "No database changes made."
            )

        parsed_lookup[key] = row

    connection = get_db_connection()

    if connection is None:
        raise RuntimeError("Could not connect to MySQL.")

    cursor = None

    try:
        cursor = connection.cursor(dictionary=True)

        # 2. Fetch only existing rows belonging to document 9
        cursor.execute(
            """
            SELECT transaction_id, transaction_date, description, debit, credit
            FROM transactions
            WHERE document_id = %s
            ORDER BY transaction_id
            """,
            (DOCUMENT_ID,),
        )

        stored_rows = cursor.fetchall()

        if len(stored_rows) != 31:
            raise RuntimeError(
                f"Expected 31 stored rows for document {DOCUMENT_ID}, "
                f"found {len(stored_rows)}. No changes made."
            )

        # 3. Verify every stored row has exactly one parsed match
        updates = []
        matched_keys = set()

        for stored in stored_rows:
            stored_date = stored["transaction_date"].isoformat()
            key = (stored_date, stored["description"])

            if key not in parsed_lookup:
                raise RuntimeError(
                    f"No parsed match for stored transaction "
                    f"ID {stored['transaction_id']}: {key}. "
                    "No changes made."
                )

            if key in matched_keys:
                raise RuntimeError(
                    f"Multiple stored rows have the same key: {key}. "
                    "No changes made."
                )

            matched_keys.add(key)
            parsed = parsed_lookup[key]

            new_debit = money(parsed["debit"])
            new_credit = money(parsed["credit"])

            # Confirm the parser assigned one side, not both
            if new_debit > 0 and new_credit > 0:
                raise RuntimeError(
                    f"Both debit and credit are positive for {key}. "
                    "No changes made."
                )

            updates.append(
                (
                    new_debit if new_debit > 0 else None,
                    new_credit if new_credit > 0 else None,
                    stored["transaction_id"],
                )
            )

        if len(matched_keys) != len(parsed_lookup):
            raise RuntimeError(
                "Some parsed transactions were not matched to stored rows. "
                "No changes made."
            )

        # 4. Update existing rows only; no INSERT statements
        for new_debit, new_credit, transaction_id in updates:
            cursor.execute(
                """
                UPDATE transactions
                SET debit = %s, credit = %s
                WHERE transaction_id = %s
                  AND document_id = %s
                """,
                (new_debit, new_credit, transaction_id, DOCUMENT_ID),
            )

        connection.commit()

        print("Correction completed successfully.")
        print("Document ID:", DOCUMENT_ID)
        print("Existing rows updated:", len(updates))
        print("No transactions inserted.")

        total_debits = sum(
            (debit or Decimal("0.00") for debit, _, _ in updates),
            Decimal("0.00"),
        )
        total_credits = sum(
            (credit or Decimal("0.00") for _, credit, _ in updates),
            Decimal("0.00"),
        )

        print("Corrected debit total:", total_debits)
        print("Corrected credit total:", total_credits)

    except Exception:
        connection.rollback()
        raise

    finally:
        if cursor is not None:
            cursor.close()
        connection.close()


if __name__ == "__main__":
    main()