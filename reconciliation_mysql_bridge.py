"""MySQL persistence bridge for FinWell multi-account reconciliation.

Creates or reuses the correct document record, saves validated transactions
only when the document has no transaction rows, maps every input transaction
to its persisted MySQL transaction_id, and stores reconciler matches.
"""

from collections import defaultdict, deque
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from pathlib import Path

from mysql_pipeline.account_storage import get_account_by_id
from mysql_pipeline.document_storage import (
    save_document,
    get_document_by_id,
    update_document_status,
)
from mysql_pipeline.duplicate_detector import check_duplicate_document
from mysql_pipeline.transaction_storage import (
    save_transactions,
    list_document_transactions,
)
from mysql_pipeline.reconciliation_storage import save_reconciliation_match


def _normal_date(value):
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if value is None:
        raise ValueError("Transaction is missing its date.")
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text[:10], fmt).date().isoformat()
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date().isoformat()
    except ValueError as exc:
        raise ValueError(f"Unsupported transaction date: {value!r}") from exc


def _normal_money(value, *, none_is_zero=True, absolute=True):
    if value is None or value == "":
        return Decimal("0.00") if none_is_zero else None
    try:
        amount = Decimal(str(value).replace(",", "").replace("₹", "").strip())
        if absolute:
            amount = abs(amount)
        return amount.quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"Invalid transaction amount: {value!r}") from exc


def _signature(transaction, *, database_row=False):
    date_value = (
        transaction.get("transaction_date")
        if database_row
        else transaction.get("date", transaction.get("transaction_date"))
    )
    return (
        _normal_date(date_value),
        " ".join(str(transaction.get("description") or "").upper().split()),
        _normal_money(transaction.get("debit")),
        _normal_money(transaction.get("credit")),
        _normal_money(
            transaction.get("balance"), none_is_zero=False, absolute=False
        ),
    )


def _sha256_file(path):
    digest = sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _get_or_create_document(user_id, mysql_account_id, pdf_path):
    """Find this exact PDF for this user, or create a linked document row."""
    path = Path(pdf_path).expanduser().resolve()
    file_hash = _sha256_file(path)

    account = get_account_by_id(user_id=int(user_id), account_id=int(mysql_account_id))
    if not account.get("success"):
        raise RuntimeError(
            f"MySQL account_id={mysql_account_id} is not owned by user_id={user_id}: "
            f"{account.get('message')}"
        )

    duplicate = check_duplicate_document(int(user_id), file_hash)
    if not duplicate.get("success"):
        raise RuntimeError(f"Could not check duplicate PDF: {duplicate.get('message')}")

    if duplicate.get("is_duplicate"):
        document_id = int(duplicate["document_id"])
        found = get_document_by_id(document_id, int(user_id))
        if not found.get("success"):
            raise RuntimeError(found.get("message", "Existing document lookup failed."))
        document = found["document"]
        if int(document.get("account_id") or 0) != int(mysql_account_id):
            raise RuntimeError(
                f"This PDF already exists as document_id={document_id}, but its account_id "
                f"is {document.get('account_id')!r}, not {mysql_account_id}. "
                "No records were changed. Resolve the existing document association first."
            )
        return document_id, True

    saved = save_document(
        user_id=int(user_id),
        original_filename=path.name,
        stored_filename=path.name,
        file_path=str(path),
        file_hash=file_hash,
        document_type="bank_statement",
        page_count=0,
        account_id=int(mysql_account_id),
    )
    if not saved.get("success") or not saved.get("document_id"):
        raise RuntimeError(f"Could not create MySQL document: {saved.get('message')}")
    return int(saved["document_id"]), False


def attach_mysql_transaction_ids(user_id, document_id, transactions):
    """Map each validated transaction to exactly one stored DB row."""
    db_result = list_document_transactions(int(document_id), int(user_id))
    if not db_result.get("success"):
        raise RuntimeError(
            f"Could not retrieve transactions for document {document_id}: "
            f"{db_result.get('message')}"
        )

    rows = db_result.get("transactions", [])
    buckets = defaultdict(deque)
    for row in rows:
        buckets[_signature(row, database_row=True)].append(row)

    input_counts = defaultdict(int)
    for transaction in transactions:
        input_counts[_signature(transaction)] += 1
    db_counts = {key: len(queue) for key, queue in buckets.items()}

    if dict(input_counts) != db_counts:
        missing, extra = [], []
        for key in set(input_counts) | set(db_counts):
            if input_counts.get(key, 0) > db_counts.get(key, 0):
                missing.append({"signature": repr(key), "pipeline_count": input_counts[key], "database_count": db_counts.get(key, 0)})
            elif db_counts.get(key, 0) > input_counts.get(key, 0):
                extra.append({"signature": repr(key), "pipeline_count": input_counts.get(key, 0), "database_count": db_counts[key]})
        raise RuntimeError(
            f"Transaction mapping is not one-to-one for document {document_id}. "
            f"No reconciliation matches will be saved. Pipeline rows missing in MySQL: "
            f"{missing[:5]}; extra MySQL rows: {extra[:5]}"
        )

    mapped = []
    for transaction in transactions:
        queue = buckets[_signature(transaction)]
        row = queue.popleft()
        tagged = dict(transaction)
        tagged["transaction_id"] = int(row["transaction_id"])
        tagged["document_id"] = int(document_id)
        mapped.append(tagged)
    return mapped


def persist_statement_transactions(user_id, mysql_account_id, pdf_path, transactions):
    """Create/reuse document, insert only if empty, then return mapped rows."""
    document_id, was_duplicate = _get_or_create_document(
        user_id, mysql_account_id, pdf_path
    )
    current = list_document_transactions(document_id, int(user_id))
    if not current.get("success"):
        raise RuntimeError(current.get("message", "Could not inspect existing transactions."))

    existing_count = len(current.get("transactions", []))
    if existing_count == 0 and transactions:
        status = update_document_status(document_id, int(user_id), "processing")
        if not status.get("success"):
            raise RuntimeError(f"Could not mark document processing: {status.get('message')}")
        saved = save_transactions(int(user_id), document_id, transactions)
        if not saved.get("success"):
            update_document_status(document_id, int(user_id), "failed", saved.get("message"))
            raise RuntimeError(f"Could not save transactions: {saved.get('message')}")
    elif existing_count not in (0, len(transactions)):
        raise RuntimeError(
            f"Document {document_id} already has {existing_count} transactions, "
            f"but this PDF produced {len(transactions)}. Refusing to append or duplicate rows."
        )

    mapped = attach_mysql_transaction_ids(user_id, document_id, transactions)
    # Existing completed duplicate documents should remain untouched. Only
    # mark the document completed when this run actually inserted its rows.
    if existing_count == 0 and transactions:
        status = update_document_status(document_id, int(user_id), "completed")
        if not status.get("success"):
            raise RuntimeError(
                f"Transactions mapped, but document status update failed: {status.get('message')}"
            )

    return {
        "document_id": document_id,
        "mysql_account_id": int(mysql_account_id),
        "document_reused": was_duplicate,
        "transactions_inserted": existing_count == 0 and bool(transactions),
        "transaction_count": len(mapped),
        "transactions": mapped,
    }


def persist_internal_transfer_matches(user_id, matches):
    results = []
    for match in matches:
        debit_id = int(match["debit_transaction_id"])
        credit_id = int(match["credit_transaction_id"])
        reference = match.get("reference")
        amount = match.get("amount")
        date_diff = match.get("date_difference_days")
        debit_account = match.get("debit_account_id")
        credit_account = match.get("credit_account_id")
        matching_score = match.get("matching_score")

        # The reconciler's raw score is evidence ranking, not a probability.
        # Use conservative categorical confidence values rather than storing
        # the raw score in the decimal confidence column.
        confidence = 0.99 if reference else 0.85
        evidence = (
            f"matching transfer reference {reference}"
            if reference
            else "transfer-related descriptions on both transactions"
        )
        reason = (
            f"Internal transfer: {evidence}; amount={amount}; "
            f"date_difference_days={date_diff}; matching_score={matching_score}; "
            f"debit_account={debit_account}; credit_account={credit_account}."
        )
        saved = save_reconciliation_match(
            user_id=int(user_id),
            transaction_id=debit_id,
            matched_transaction_id=credit_id,
            match_type="internal_transfer",
            confidence_score=confidence,
            match_reason=reason,
        )
        results.append({
            "reconciler_match_id": match.get("match_id"),
            "debit_transaction_id": debit_id,
            "credit_transaction_id": credit_id,
            "reference": reference,
            "amount": amount,
            "confidence_score": confidence,
            **saved,
        })

    failures = [item for item in results if not item.get("success")]
    return {
        "success": not failures,
        "attempted": len(results),
        "saved_or_existing": sum(1 for item in results if item.get("success")),
        "failed": len(failures),
        "results": results,
    }
