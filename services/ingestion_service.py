
import hashlib
import logging
import shutil
import uuid
from pathlib import Path

from pdf_extraction.pdf_validator import validate_pdf
from pdf_extraction.pdf_reader import extract_pdf_text
from pdf_extraction.document_classifier import classify_document

from preprocessing.text_cleaner import clean_extracted_text
from preprocessing.transaction_parser import parse_transactions
from preprocessing.data_normalizer import normalize_transactions
from preprocessing.data_validator import validate_transactions

from chroma_pipeline.chunker import chunk_text
from chroma_pipeline.vector_store import add_document_chunks

from mysql_pipeline.account_storage import get_account_by_id

from mysql_pipeline.document_storage import (
    save_document,
    update_document_status,
    update_document_type,
)

from mysql_pipeline.duplicate_detector import check_duplicate_document
from mysql_pipeline.transaction_storage import save_transactions
from reconciliation.ingestion_shadow_service import (
    analyze_incoming_transactions,
)


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
UPLOADS_DIR = PROJECT_ROOT / "data" / "uploads"

logger = logging.getLogger(__name__)


# ============================================================
# FILE UTILITIES
# ============================================================

def calculate_file_hash(file_path):
    """Calculate the SHA-256 hash of a file."""

    sha256 = hashlib.sha256()

    with open(file_path, "rb") as file:
        for block in iter(lambda: file.read(8192), b""):
            sha256.update(block)

    return sha256.hexdigest()


def create_permanent_copy(source_path, user_id):
    """
    Copy a PDF into the user's permanent upload folder.

    Returns:
        dict containing success, stored_filename and stored_path.
    """

    source_path = Path(source_path)

    try:
        user_upload_dir = UPLOADS_DIR / f"user_{user_id}"
        user_upload_dir.mkdir(parents=True, exist_ok=True)

        unique_filename = f"{uuid.uuid4().hex}.pdf"
        destination_path = user_upload_dir / unique_filename

        shutil.copy2(source_path, destination_path)

        return {
            "success": True,
            "stored_filename": unique_filename,
            "stored_path": destination_path.resolve(),
        }

    except OSError:
        logger.exception(
            "Could not create permanent PDF copy for user_id=%s",
            user_id,
        )

        return {
            "success": False,
            "message": "Could not store the uploaded PDF.",
        }


def _mark_document_failed(document_id, user_id, error):
    """
    Safely attempt to mark a registered document as failed.

    The original document record and permanent PDF are retained.
    """

    if document_id is None:
        return False

    try:
        result = update_document_status(
            document_id=document_id,
            user_id=user_id,
            status="failed",
            error_message=str(error),
        )

        if not result or not result.get("success"):
            logger.error(
                "Could not mark document_id=%s as failed: %s",
                document_id,
                result,
            )
            return False

        return True

    except Exception:
        logger.exception(
            "Exception while marking document_id=%s as failed",
            document_id,
        )
        return False


# ============================================================


def _auto_detect_or_create_account(pdf_path, user_id):
    """
    Attempt to auto-detect account details from the PDF statement header.
    If an existing account with the same masked number exists for this user, reuse it.
    Otherwise, automatically create a new account in MySQL so transactions are linked.
    """
    try:
        import pymupdf
        import re
        from mysql_pipeline.db import get_db_connection

        doc = pymupdf.open(str(pdf_path))
        raw_text = doc[0].get_text() if len(doc) > 0 else ""
        doc.close()

        if not raw_text:
            return None

        # Extract institution name dynamically from header lines
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        bank_name = "Primary Bank"
        for line in lines[:6]:
            if re.search(r'\b(?:bank|credit\s*union|financial|bancorp|securities)\b', line, re.I):
                bank_name = line.strip().title()
                break
        if bank_name == "Primary Bank" and lines:
            if len(lines[0]) <= 50 and not re.search(r'statement|account|page|date|customer', lines[0], re.I):
                bank_name = lines[0].strip().title()

        acc_match = re.search(r'(?:Account|A/c)\s*(?:No\.?|Number|#)?\s*[:\s]*([X\d\s-]{4,24}\d{4})', raw_text, re.I)
        raw_acc = acc_match.group(1).strip() if acc_match else ''
        last4 = re.findall(r'\d{4}', raw_acc)
        if not last4:
            return None
        last4_str = last4[-1]
        masked_acc = f'XXXX{last4_str}'

        type_match = re.search(r'Account\s*Type\s*[:\s]*([A-Za-z\s]+)', raw_text, re.I)
        acc_type_raw = type_match.group(1).strip().lower() if type_match else 'savings'
        acc_type = 'savings' if 'savings' in acc_type_raw else ('current' if 'current' in acc_type_raw else 'savings')

        curr_match = re.search(r'Currency\s*[:\s]*([A-Za-z]{3})', raw_text, re.I)
        currency = curr_match.group(1).upper() if curr_match else 'INR'
        account_name = f'{bank_name} {acc_type.capitalize()} ({last4_str})'

        conn = get_db_connection()
        if not conn:
            return None
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            "SELECT account_id FROM accounts WHERE user_id = %s AND masked_account_number = %s",
            (user_id, masked_acc)
        )
        existing = cursor.fetchone()
        if existing:
            account_id = existing["account_id"]
        else:
            cursor.execute(
                """
                INSERT INTO accounts (user_id, account_name, institution_name, account_type, masked_account_number, currency, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
                """,
                (user_id, account_name, bank_name, acc_type, masked_acc, currency)
            )
            conn.commit()
            account_id = cursor.lastrowid

        cursor.close()
        conn.close()
        return account_id
    except Exception as exc:
        logger.warning("Could not auto-detect account for user_id=%s: %s", user_id, exc)
        return None


def _auto_discover_reconciliation_matches(user_id):
    """
    Scan all reconciliation engines (internal transfers, duplicates, and refunds)
    and persist discovered candidates into reconciliation_matches dynamically.
    """
    try:
        from reconciliation.unified_reconciliation_service import (
            reconcile_user_from_database,
        )
        from mysql_pipeline.reconciliation_storage import (
            save_reconciliation_match,
        )

        res = reconcile_user_from_database(user_id)
        engines = res.get("reconciliation", {}).get("engines", {})

        # 1. Internal Transfers
        transfers = engines.get("internal_transfers", {}).get("candidates", [])
        for c in transfers:
            ref = c.get("reference")
            amt = c.get("amount")
            gap = c.get("date_gap_days", 0)
            src = c.get("source_account_id")
            tgt = c.get("target_account_id")
            reason = (
                f"Internal transfer: matching transfer reference {ref}; "
                f"amount={amt}; date_difference_days={gap}; "
                f"debit_account={src}; credit_account={tgt}."
            )
            save_reconciliation_match(
                user_id=user_id,
                transaction_id=c["debit_transaction_id"],
                matched_transaction_id=c["credit_transaction_id"],
                match_type="internal_transfer",
                confidence_score=0.99,
                match_reason=reason,
            )

        # 2. Duplicate Transactions
        comparisons = engines.get("duplicates", {}).get("comparisons", [])
        for comp in comparisons:
            comp_res = comp.get("result", {})
            if comp_res.get("is_candidate"):
                tx1 = comp.get("transaction1_id")
                tx2 = comp.get("transaction2_id")
                score = comp_res.get("confidence_score", 0.90)
                reason = comp_res.get("match_reason") or "Potential duplicate transaction detected."
                if tx1 and tx2 and tx1 != tx2:
                    save_reconciliation_match(
                        user_id=user_id,
                        transaction_id=tx1,
                        matched_transaction_id=tx2,
                        match_type="duplicate",
                        confidence_score=float(score),
                        match_reason=reason,
                    )

        # 3. Refunds
        allocations = engines.get("refunds", {}).get("allocations", [])
        for a in allocations:
            pid = a.get("purchase_transaction_id")
            rid = a.get("refund_transaction_id")
            amt = a.get("refund_amount")
            merchant = a.get("merchant") or "Merchant"
            ref = a.get("reference")
            reason = f"Refund match: {merchant} refund for amount {amt}; ref={ref}."
            if pid and rid and pid != rid:
                save_reconciliation_match(
                    user_id=user_id,
                    transaction_id=pid,
                    matched_transaction_id=rid,
                    match_type="refund",
                    confidence_score=0.95,
                    match_reason=reason,
                )

    except Exception as exc:
        logger.warning(
            "Auto reconciliation scan skipped for user %s: %s",
            user_id,
            exc,
        )


_auto_discover_transfer_matches = _auto_discover_reconciliation_matches


# MAIN INGESTION SERVICE
# ============================================================

def ingest_document(pdf_path, user_id, account_id=None):
    """
    Ingest a financial PDF into permanent storage, MySQL and ChromaDB.

    Optional account_id:
        If supplied, account ownership is validated.
        If omitted, the document remains unassociated with an account.

    Processing sequence:

        1. Validate account ownership
        2. Validate PDF
        3. Calculate SHA-256 hash
        4. Check duplicate document
        5. Create permanent PDF copy
        6. Save document record in MySQL
        7. Mark document as processing
        8. Extract PDF text
        9. Clean extracted text
        10. Classify document
        11. Save document type
        12. Parse transactions
        13. Normalize transactions
        14. Validate transactions
        15. Save valid transactions in MySQL
        16. Create text chunks
        17. Store chunks in ChromaDB
        18. Mark document completed

    Important:
        MySQL and ChromaDB do not share an atomic transaction.
        If one storage operation succeeds and a later operation fails,
        manual or future automated recovery may be required.
    """

    source_path = Path(pdf_path)

    document_id = None
    stored_path = None

    # Result counters
    transaction_count = 0
    valid_transaction_count = 0
    invalid_transaction_count = 0
    stored_transaction_count = 0
    chunk_count = 0

    document_type = "unknown"
    cleaned_text = ""

    # --------------------------------------------------------
    # STEP 1: Validate user and optional account
    # --------------------------------------------------------

    if (
        not isinstance(user_id, int)
        or isinstance(user_id, bool)
        or user_id <= 0
    ):
        return {
            "success": False,
            "stage": "account_validation",
            "message": "user_id must be a positive integer.",
        }

    detected_acc_id = _auto_detect_or_create_account(source_path, user_id)
    if account_id is None:
        account_id = detected_acc_id
    elif detected_acc_id is not None and detected_acc_id != account_id:
        logger.info(
            'Account mismatch in header: user selected account_id=%s, '
            'but statement indicates account_id=%s. Re-routing to detected account.',
            account_id,
            detected_acc_id,
        )
        account_id = detected_acc_id

    if account_id is not None:

        if (
            not isinstance(account_id, int)
            or isinstance(account_id, bool)
            or account_id <= 0
        ):
            return {
                "success": False,
                "stage": "account_validation",
                "message": "account_id must be a positive integer.",
                "account_id": account_id,
            }

        try:
            account_result = get_account_by_id(
                user_id=user_id,
                account_id=account_id,
            )

            if (
                not account_result
                or not account_result.get("success")
                or not account_result.get("account")
            ):
                return {
                    "success": False,
                    "stage": "account_validation",
                    "message": (
                        "The selected account does not exist "
                        "or does not belong to this user."
                    ),
                    "account_id": account_id,
                }

        except Exception:
            logger.exception(
                "Account ownership validation failed for user_id=%s",
                user_id,
            )

            return {
                "success": False,
                "stage": "account_validation",
                "message": "Could not validate the selected account.",
                "account_id": account_id,
            }

    # --------------------------------------------------------
    # STEP 2: Validate PDF
    # --------------------------------------------------------

    try:
        pdf_validation_result = validate_pdf(str(source_path))

        if not pdf_validation_result.get("valid"):
            return {
                "success": False,
                "stage": "validation",
                "message": pdf_validation_result.get(
                    "error",
                    "PDF validation failed.",
                ),
                "account_id": account_id,
            }

        page_count = pdf_validation_result.get("total_pages", 0)

    except Exception:
        logger.exception("PDF validation raised an exception.")

        return {
            "success": False,
            "stage": "validation",
            "message": "Could not validate the uploaded PDF.",
            "account_id": account_id,
        }

    # --------------------------------------------------------
    # STEP 3: Calculate file hash
    # --------------------------------------------------------

    try:
        file_hash = calculate_file_hash(source_path)

    except Exception:
        logger.exception("PDF hashing failed.")

        return {
            "success": False,
            "stage": "file_hash",
            "message": "Could not calculate the PDF file hash.",
            "account_id": account_id,
        }

    # --------------------------------------------------------
    # STEP 4: Duplicate detection
    # --------------------------------------------------------

    try:
        duplicate_result = check_duplicate_document(
            user_id=user_id,
            file_hash=file_hash,
        )

        if not duplicate_result.get("success"):
            return {
                "success": False,
                "stage": "duplicate_check",
                "message": duplicate_result.get(
                    "message",
                    "Duplicate check failed.",
                ),
                "account_id": account_id,
            }

        if duplicate_result.get("is_duplicate"):
            return {
                "success": False,
                "stage": "duplicate_check",
                "is_duplicate": True,
                "existing_document_id": duplicate_result.get(
                    "document_id"
                ),
                "message": (
                    "This PDF has already been uploaded by this user."
                ),
                "account_id": account_id,
            }

    except Exception:
        logger.exception(
            "Duplicate detection failed for user_id=%s",
            user_id,
        )

        return {
            "success": False,
            "stage": "duplicate_check",
            "message": "Could not check for duplicate documents.",
            "account_id": account_id,
        }

    # --------------------------------------------------------
    # STEP 5: Create permanent PDF copy
    # --------------------------------------------------------

    storage_result = create_permanent_copy(
        source_path=source_path,
        user_id=user_id,
    )

    if not storage_result.get("success"):
        return {
            "success": False,
            "stage": "file_storage",
            "message": storage_result.get(
                "message",
                "Failed to store PDF permanently.",
            ),
            "account_id": account_id,
        }

    stored_filename = storage_result["stored_filename"]
    stored_path = Path(storage_result["stored_path"])

    # --------------------------------------------------------
    # STEP 6: Register document in MySQL
    # --------------------------------------------------------

    try:
        document_result = save_document(
            user_id=user_id,
            original_filename=source_path.name,
            stored_filename=stored_filename,
            file_path=str(stored_path),
            file_hash=file_hash,
            document_type="unknown",
            page_count=page_count,
            account_id=account_id,
        )

        if not document_result.get("success"):

            # No document record was successfully registered.
            # Remove the untracked permanent file.
            try:
                stored_path.unlink(missing_ok=True)
            except OSError:
                logger.exception(
                    "Could not remove untracked PDF copy: %s",
                    stored_path,
                )

            return {
                "success": False,
                "stage": "mysql_document_storage",
                "message": document_result.get(
                    "message",
                    "Failed to save document record.",
                ),
                "account_id": account_id,
            }

        document_id = document_result.get("document_id")

        if not document_id:
            raise RuntimeError(
                "Document storage did not return a document ID."
            )

    except Exception:
        logger.exception(
            "Document registration failed for user_id=%s",
            user_id,
        )

        # Do not delete the permanent file here: an uncertain database
        # outcome should not cause us to remove a possibly registered file.
        return {
            "success": False,
            "stage": "mysql_document_storage",
            "message": "Could not register the document in MySQL.",
            "account_id": account_id,
        }

    # --------------------------------------------------------
    # STEP 7: Mark document as processing
    # --------------------------------------------------------

    try:
        status_result = update_document_status(
            document_id=document_id,
            user_id=user_id,
            status="processing",
        )

        if not status_result.get("success"):
            raise RuntimeError(
                status_result.get(
                    "message",
                    "Could not mark document as processing.",
                )
            )

    except Exception as error:
        logger.exception(
            "Could not mark document_id=%s as processing",
            document_id,
        )

        _mark_document_failed(
            document_id,
            user_id,
            error,
        )

        return {
            "success": False,
            "stage": "mysql_status_update",
            "document_id": document_id,
            "account_id": account_id,
            "message": "Could not start document processing.",
        }

    # --------------------------------------------------------
    # STEPS 8-18: Process document
    # --------------------------------------------------------

    try:

        # STEP 8: Extract PDF text
        extraction_result = extract_pdf_text(str(stored_path))

        if not extraction_result.get("success"):
            raise RuntimeError(
                extraction_result.get(
                    "error",
                    "PDF text extraction failed.",
                )
            )

        extracted_text = extraction_result.get("full_text", "")

        if not extracted_text.strip():
            raise RuntimeError(
                "No selectable text was found. "
                "OCR is not enabled for scanned PDFs yet."
            )

        # STEP 9: Clean extracted text
        cleaning_result = clean_extracted_text(extracted_text)

        if not cleaning_result.get("success"):
            raise RuntimeError(
                cleaning_result.get(
                    "error",
                    "Text cleaning failed.",
                )
            )

        cleaned_text = cleaning_result.get("cleaned_text", "")

        if not cleaned_text.strip():
            raise RuntimeError("No text remained after cleaning.")

        # STEP 10: Classify document
        classification_result = classify_document(cleaned_text)

        if not classification_result.get("success"):
            raise RuntimeError(
                classification_result.get(
                    "error",
                    "Document classification failed.",
                )
            )

        document_type = classification_result.get(
            "document_type",
            "unknown",
        )

        # STEP 11: Save document type
        type_result = update_document_type(
            document_id=document_id,
            user_id=user_id,
            document_type=document_type,
        )

        if not type_result.get("success"):
            raise RuntimeError(
                type_result.get(
                    "message",
                    "Failed to update document type in MySQL.",
                )
            )

        # STEP 12: Parse transactions
        parsing_result = parse_transactions(cleaned_text)

        if not parsing_result.get("success"):
            raise RuntimeError(
                parsing_result.get(
                    "error",
                    "Transaction parsing failed.",
                )
            )

        parsed_transactions = parsing_result.get("transactions", [])

        transaction_count = len(parsed_transactions)

        # STEP 13: Normalize transactions
        normalization_result = normalize_transactions(
            parsed_transactions
        )

        if not normalization_result.get("success"):
            raise RuntimeError(
                normalization_result.get(
                    "error",
                    "Transaction normalization failed.",
                )
            )

        normalized_transactions = normalization_result.get(
            "transactions",
            [],
        )

               # ----------------------------------------------------
        # STEP 14: Validate normalized transactions
        # ----------------------------------------------------

        transaction_validation_result = validate_transactions(
            normalized_transactions
        )

        if not transaction_validation_result.get("success"):
            raise RuntimeError(
                transaction_validation_result.get(
                    "message",
                    "Transaction validation failed.",
                )
            )

        valid_transactions = (
            transaction_validation_result.get(
                "valid_transactions",
                [],
            )
        )

        invalid_transaction_count = (
            transaction_validation_result.get(
                "invalid_count",
                0,
            )
        )

        valid_transaction_count = (
            transaction_validation_result.get(
                "valid_count",
                len(valid_transactions),
            )
        )

        # ----------------------------------------------------
        # STEP 14.5: SHADOW RECONCILIATION
        # ----------------------------------------------------
        # This stage is read-only.
        # It does not save reconciliation cases or matches.
        # Failure here must not interrupt normal ingestion.

        reconciliation_shadow_result = (
            analyze_incoming_transactions(
                user_id=user_id,
                document_id=document_id,
                account_id=account_id,
                transactions=valid_transactions,
            )
        )

        if not reconciliation_shadow_result.get("success"):
            logger.warning(
                "Shadow reconciliation failed for document_id=%s: %s",
                document_id,
                reconciliation_shadow_result.get("message"),
            )

        elif reconciliation_shadow_result.get("skipped"):
            logger.info(
                "Shadow reconciliation skipped for document_id=%s: %s",
                document_id,
                reconciliation_shadow_result.get("message"),
            )

        else:
            logger.info(
                "Shadow reconciliation completed for document_id=%s. "
                "Candidates=%s, pairs_checked=%s",
                document_id,
                reconciliation_shadow_result.get(
                    "duplicate_candidate_count",
                    0,
                ),
                reconciliation_shadow_result.get(
                    "pairs_checked",
                    0,
                ),
            )

        # STEP 15: Store validated transactions in MySQL
        if valid_transactions:

            transaction_save_result = save_transactions(
                user_id=user_id,
                document_id=document_id,
                transactions=valid_transactions,
            )

            if not transaction_save_result.get("success"):
                raise RuntimeError(
                    transaction_save_result.get(
                        "message",
                        "Failed to save transactions in MySQL.",
                    )
                )

            stored_transaction_count = len(valid_transactions)

        # STEP 16: Create text chunks only after successful
        # transaction parsing, normalization and validation.
        chunks = chunk_text(
            cleaned_text,
            chunk_size=1000,
            chunk_overlap=150,
        )

        if not chunks:
            raise RuntimeError("No text chunks were created.")

        # STEP 17: Store chunks in ChromaDB
        chroma_result = add_document_chunks(
            document_id=document_id,
            user_id=user_id,
            chunks=chunks,
            account_id=account_id,
        )

        if not chroma_result.get("success"):
            raise RuntimeError(
                chroma_result.get(
                    "message",
                    "ChromaDB storage failed.",
                )
            )

        chunk_count = chroma_result.get("stored_count", 0)

        _auto_discover_transfer_matches(user_id)

        # STEP 18: Mark document completed only after both
        # MySQL transaction storage and ChromaDB indexing succeed.
        status_result = update_document_status(
            document_id=document_id,
            user_id=user_id,
            status="completed",
        )

        if not status_result.get("success"):
            raise RuntimeError(
                status_result.get(
                    "message",
                    "Failed to mark document as completed.",
                )
            )

        # ----------------------------------------------------
        # SUCCESS RESPONSE
        # ----------------------------------------------------

              # ----------------------------------------------------
        # SUCCESS RESPONSE
        # ----------------------------------------------------

        return {
            "success": True,
            "stage": "completed",
            "message": "Document ingestion completed successfully.",

            "document_id": document_id,
            "user_id": user_id,
            "account_id": account_id,

            "filename": source_path.name,
            "stored_filename": stored_filename,
            "file_path": str(stored_path),

            "document_type": document_type,
            "page_count": page_count,
            "character_count": len(cleaned_text),

            "chunk_count": chunk_count,

            "parsed_transaction_count": transaction_count,
            "valid_transaction_count": valid_transaction_count,
            "invalid_transaction_count": invalid_transaction_count,
            "stored_transaction_count": stored_transaction_count,

            "reconciliation_shadow": reconciliation_shadow_result,
        }

    # --------------------------------------------------------
    # FAILURE HANDLING
    # --------------------------------------------------------

    except Exception as error:

        logger.exception(
            "Document ingestion failed for document_id=%s",
            document_id,
        )

        failure_status_updated = _mark_document_failed(
            document_id=document_id,
            user_id=user_id,
            error=error,
        )

        return {
            "success": False,
            "stage": "processing",
            "document_id": document_id,
            "user_id": user_id,
            "account_id": account_id,
            "filename": source_path.name,
            "file_path": str(stored_path),
            "message": "Document processing failed.",
            "error_detail": str(error),
            "failure_status_updated": failure_status_updated,
            "parsed_transaction_count": transaction_count,
            "valid_transaction_count": valid_transaction_count,
            "invalid_transaction_count": invalid_transaction_count,
            "stored_transaction_count": stored_transaction_count,
            "chunk_count": chunk_count,
        }
