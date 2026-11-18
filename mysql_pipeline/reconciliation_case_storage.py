"""Case-based reconciliation storage for FinWell AI.

This module persists reconciliation cases and their supporting records. It does
not detect matches, alter original transactions, or make financial decisions.

All write operations use parameterized SQL and explicit transactions. Financial
allocations are validated against both transaction sides and serialized by
locking the underlying transaction rows in a consistent order.
"""

from decimal import Decimal, InvalidOperation
import json

from mysql.connector import Error

from mysql_pipeline.db import get_db_connection


VALID_CASE_TYPES = {
    "duplicate", "internal_transfer", "refund", "settlement",
    "merchant_verification", "balance_discrepancy",
}
VALID_CASE_STATUSES = {
    "detected", "evaluated", "suggested", "confirmed", "rejected",
    "needs_review", "reopened", "unmatched", "partially_matched",
}
VALID_PARTICIPANT_ROLES = {"source", "target", "member", "unmatched_candidate"}
VALID_PARTICIPANT_STATUSES = {"proposed", "accepted", "rejected", "unmatched"}
VALID_EVIDENCE_TYPES = {
    "transaction_reference", "amount_match", "date_match", "description_match",
    "statement_balance", "merchant_match", "document_reference", "other",
}
VALID_DECISION_TYPES = {"suggested", "auto_confirmed", "user_confirmed", "rejected", "reopened"}
VALID_ACTOR_TYPES = {"system", "user"}
VALID_ALLOCATION_STATUSES = {"proposed", "confirmed", "rejected"}

INITIAL_DECISION_STATUS = {
    "suggested": "suggested",
    "auto_confirmed": "confirmed",
    "user_confirmed": "confirmed",
    "rejected": "rejected",
    "reopened": "reopened",
}


def _positive_id(value, field_name):
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{field_name} must be a positive integer.")
    return value


def _confidence(value):
    if value is None:
        return None
    try:
        score = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("confidence_score must be a valid number.") from exc
    if not score.is_finite() or not Decimal("0") <= score <= Decimal("1"):
        raise ValueError("confidence_score must be between 0 and 1.")
    return score


def _money(value, field_name="amount"):
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a valid decimal amount.") from exc
    if not amount.is_finite():
        raise ValueError(f"{field_name} must be finite.")
    if amount.as_tuple().exponent < -2:
        raise ValueError(f"{field_name} cannot have more than two decimal places.")
    if abs(amount) >= Decimal("10000000000000000"):
        raise ValueError(f"{field_name} exceeds the supported DECIMAL(18,2) range.")
    return amount


def _json_value(value):
    return None if value is None else json.dumps(value, ensure_ascii=False, default=str)


def _verify_actor(user_id, actor_type, actor_user_id):
    if actor_type not in VALID_ACTOR_TYPES:
        raise ValueError("Invalid actor_type.")
    if actor_type == "user":
        _positive_id(actor_user_id, "actor_user_id")
        if actor_user_id != user_id:
            raise ValueError("Actor does not belong to this reconciliation case.")
    elif actor_user_id is not None:
        raise ValueError("System actions must not specify actor_user_id.")


def _case_owner_for_update(cursor, case_id):
    cursor.execute(
        "SELECT user_id, case_status FROM reconciliation_cases WHERE case_id = %s FOR UPDATE",
        (case_id,),
    )
    return cursor.fetchone()


def _verify_transaction_owner(cursor, transaction_id, user_id, lock=False):
    query = "SELECT transaction_id FROM transactions WHERE transaction_id = %s AND user_id = %s"
    if lock:
        query += " FOR UPDATE"
    cursor.execute(query, (transaction_id, user_id))
    if cursor.fetchone() is None:
        raise ValueError("Transaction not found for this user.")


def _insert_audit(cursor, case_id, event_type, description, data, actor_type, actor_user_id):
    cursor.execute(
        """INSERT INTO reconciliation_audit_events
           (case_id, event_type, event_description, event_data, actor_type, actor_user_id)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        (case_id, event_type, description, _json_value(data), actor_type, actor_user_id),
    )
    return cursor.lastrowid


def _transaction_financial_profile(cursor, transaction_id, user_id):
    """Read amount, direction and linked-account currency for an owned transaction."""
    cursor.execute(
        """SELECT t.transaction_id, t.debit, t.credit, t.account_id, a.currency
           FROM transactions t
           LEFT JOIN accounts a
             ON a.account_id = t.account_id AND a.user_id = t.user_id
           WHERE t.transaction_id = %s AND t.user_id = %s""",
        (transaction_id, user_id),
    )
    row = cursor.fetchone()
    if row is None:
        raise ValueError("Transaction not found for this user.")

    debit = _money(row[1] or 0, "debit")
    credit = _money(row[2] or 0, "credit")
    if debit < 0 or credit < 0 or (debit > 0 and credit > 0):
        raise ValueError("Transaction must have one non-negative debit or credit amount.")
    if debit > 0:
        direction, amount = "debit", debit
    elif credit > 0:
        direction, amount = "credit", credit
    else:
        raise ValueError("Transaction has no positive debit or credit amount.")
    currency = row[4].upper() if row[4] else None
    return {"transaction_id": row[0], "direction": direction, "amount": amount,
            "account_id": row[3], "currency": currency}


def _lock_transaction_profiles(cursor, transaction_ids, user_id):
    """Lock both transactions in ID order to serialize cross-case allocations."""
    ordered_ids = sorted(set(transaction_ids))
    placeholders = ",".join(["%s"] * len(ordered_ids))
    cursor.execute(
        f"""SELECT transaction_id FROM transactions
            WHERE user_id = %s AND transaction_id IN ({placeholders})
            ORDER BY transaction_id FOR UPDATE""",
        tuple([user_id] + ordered_ids),
    )
    found = {row[0] for row in cursor.fetchall()}
    if found != set(ordered_ids):
        raise ValueError("One or more transactions were not found for this user.")


def _confirmed_allocation_totals(cursor, transaction_id, user_id):
    """Return confirmed amounts allocated out of and into this transaction."""
    cursor.execute(
        """SELECT
             COALESCE(SUM(CASE WHEN p.transaction_id = %s THEN ra.allocated_amount ELSE 0 END), 0),
             COALESCE(SUM(CASE WHEN q.transaction_id = %s THEN ra.allocated_amount ELSE 0 END), 0)
           FROM reconciliation_allocations ra
           JOIN reconciliation_participants p
             ON p.participant_id = ra.from_participant_id AND p.case_id = ra.case_id
           JOIN reconciliation_participants q
             ON q.participant_id = ra.to_participant_id AND q.case_id = ra.case_id
           WHERE ra.allocation_status = 'confirmed'
             AND p.user_id = %s AND q.user_id = %s""",
        (transaction_id, transaction_id, user_id, user_id),
    )
    outgoing, incoming = cursor.fetchone()
    return _money(outgoing or 0), _money(incoming or 0)


def _validate_allocation_pair(cursor, user_id, source_transaction_id,
                              target_transaction_id, amount, currency,
                              require_verified_currency):
    source = _transaction_financial_profile(cursor, source_transaction_id, user_id)
    target = _transaction_financial_profile(cursor, target_transaction_id, user_id)
    if source["direction"] == target["direction"]:
        raise ValueError("Allocation requires opposite transaction directions (debit and credit).")

    known_currencies = {source["currency"], target["currency"]} - {None}
    if len(known_currencies) > 1:
        raise ValueError("Source and target transactions have different account currencies.")
    if known_currencies and currency not in known_currencies:
        raise ValueError("Allocation currency does not match the linked account currency.")
    if require_verified_currency and (source["currency"] is None or target["currency"] is None):
        raise ValueError("Cannot confirm allocation until both transactions have linked accounts with verified currencies.")

    source_out, source_in = _confirmed_allocation_totals(
        cursor, source_transaction_id, user_id
    )
    target_out, target_in = _confirmed_allocation_totals(
        cursor, target_transaction_id, user_id
    )
    # A transaction can be allocated as a source or target, but its total
    # confirmed financial relationship cannot exceed its own transaction value.
    source_used = source_out + source_in
    target_used = target_out + target_in
    if source_used + amount > source["amount"]:
        raise ValueError("Confirmed allocations would exceed the source transaction amount.")
    if target_used + amount > target["amount"]:
        raise ValueError("Confirmed allocations would exceed the target transaction amount.")
    return source, target


def create_reconciliation_case(
    user_id: int, case_type: str, participants: list, *, case_status: str = None,
    confidence_score=None, algorithm_version: str = None, case_summary: str = None,
    case_details=None, evidence: list = None, decision_type: str = None,
    decision_reason: str = None, actor_type: str = "system", actor_user_id: int = None,
):
    """Create a case, participants, evidence and initial history atomically.

    Participant dictionaries require ``transaction_id`` and may include
    ``participant_role`` and ``participant_status``. Evidence dictionaries
    require ``evidence_type`` and may include description/data/document_id.
    If an initial decision is supplied, its corresponding case status is
    derived automatically unless an identical status is explicitly supplied.
    """
    connection = cursor = None
    try:
        user_id = _positive_id(user_id, "user_id")
        if case_type not in VALID_CASE_TYPES:
            raise ValueError("Invalid case_type.")
        if not isinstance(participants, list) or not participants:
            raise ValueError("At least one participant is required.")
        if case_type in {"duplicate", "internal_transfer", "refund", "settlement"} and len(participants) < 2:
            raise ValueError(f"{case_type} cases require at least two participants.")
        if decision_type is not None and decision_type not in VALID_DECISION_TYPES:
            raise ValueError("Invalid decision_type.")
        if decision_type == "auto_confirmed" and actor_type != "system":
            raise ValueError("Automatic confirmation must be recorded by the system.")
        if decision_type == "user_confirmed" and actor_type != "user":
            raise ValueError("User confirmation must identify the owning user.")
        _verify_actor(user_id, actor_type, actor_user_id)

        expected_status = INITIAL_DECISION_STATUS.get(decision_type) if decision_type else None
        if case_status is None:
            case_status = expected_status or "detected"
        if case_status not in VALID_CASE_STATUSES:
            raise ValueError("Invalid case_status.")
        if expected_status is not None and case_status != expected_status:
            raise ValueError("Initial case_status must agree with the initial decision_type.")
        if case_status in {"confirmed", "rejected", "reopened", "suggested"} and decision_type is None:
            raise ValueError("This initial case_status requires a corresponding initial decision.")
        score = _confidence(confidence_score)

        connection = get_db_connection()
        if connection is None:
            return {"success": False, "message": "Could not connect to MySQL.", "case_id": None}
        cursor = connection.cursor()

        normalized = []
        seen = set()
        for item in participants:
            if not isinstance(item, dict):
                raise ValueError("Each participant must be a dictionary.")
            transaction_id = _positive_id(item.get("transaction_id"), "transaction_id")
            role = item.get("participant_role", "member")
            status = item.get("participant_status", "proposed")
            if role not in VALID_PARTICIPANT_ROLES or status not in VALID_PARTICIPANT_STATUSES:
                raise ValueError("Invalid participant role or status.")
            if transaction_id in seen:
                raise ValueError("A transaction can appear only once in a case.")
            seen.add(transaction_id)
            normalized.append((transaction_id, role, status))

        _lock_transaction_profiles(cursor, [item[0] for item in normalized], user_id)
        cursor.execute(
            """INSERT INTO reconciliation_cases
               (user_id, case_type, case_status, confidence_score, algorithm_version,
                case_summary, case_details)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (user_id, case_type, case_status, score, algorithm_version,
             case_summary, _json_value(case_details)),
        )
        case_id = cursor.lastrowid
        participant_ids = {}
        for transaction_id, role, status in normalized:
            cursor.execute(
                """INSERT INTO reconciliation_participants
                   (case_id, user_id, transaction_id, participant_role, participant_status)
                   VALUES (%s, %s, %s, %s, %s)""",
                (case_id, user_id, transaction_id, role, status),
            )
            participant_ids[transaction_id] = cursor.lastrowid

        evidence_items = evidence or []
        if not isinstance(evidence_items, list):
            raise ValueError("evidence must be a list.")
        for item in evidence_items:
            if not isinstance(item, dict) or item.get("evidence_type") not in VALID_EVIDENCE_TYPES:
                raise ValueError("Each evidence item must have a valid evidence_type.")
            document_id = item.get("document_id")
            if document_id is not None:
                document_id = _positive_id(document_id, "document_id")
                cursor.execute(
                    "SELECT document_id FROM documents WHERE document_id = %s AND user_id = %s",
                    (document_id, user_id),
                )
                if cursor.fetchone() is None:
                    raise ValueError("Evidence document not found for this user.")
            cursor.execute(
                """INSERT INTO reconciliation_evidence
                   (case_id, evidence_type, evidence_description, evidence_data, document_id)
                   VALUES (%s, %s, %s, %s, %s)""",
                (case_id, item["evidence_type"], item.get("evidence_description"),
                 _json_value(item.get("evidence_data")), document_id),
            )

        if decision_type:
            cursor.execute(
                """INSERT INTO reconciliation_decisions
                   (case_id, decision_type, decision_reason, confidence_score, actor_type, actor_user_id)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (case_id, decision_type, decision_reason, score, actor_type, actor_user_id),
            )
        _insert_audit(
            cursor, case_id, "case_created", "Reconciliation case created.",
            {"participant_count": len(normalized), "evidence_count": len(evidence_items),
             "initial_decision": decision_type}, actor_type, actor_user_id,
        )
        connection.commit()
        return {"success": True, "message": "Reconciliation case created successfully.",
                "case_id": case_id, "participant_ids": participant_ids}
    except (Error, ValueError, TypeError, KeyError) as error:
        if connection is not None:
            connection.rollback()
        return {"success": False, "message": str(error), "case_id": None}
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


def add_case_participant(user_id: int, case_id: int, transaction_id: int,
                         participant_role: str = "member", participant_status: str = "proposed"):
    connection = cursor = None
    try:
        user_id = _positive_id(user_id, "user_id")
        case_id = _positive_id(case_id, "case_id")
        transaction_id = _positive_id(transaction_id, "transaction_id")
        if participant_role not in VALID_PARTICIPANT_ROLES or participant_status not in VALID_PARTICIPANT_STATUSES:
            raise ValueError("Invalid participant role or status.")
        connection = get_db_connection()
        if connection is None:
            return {"success": False, "message": "Could not connect to MySQL.", "participant_id": None}
        cursor = connection.cursor()
        owner = _case_owner_for_update(cursor, case_id)
        if owner is None or owner[0] != user_id:
            raise ValueError("Reconciliation case not found for this user.")
        if owner[1] in {"confirmed", "rejected"}:
            raise ValueError("Cannot add participants to a closed case. Reopen it first.")
        _lock_transaction_profiles(cursor, [transaction_id], user_id)
        cursor.execute(
            """INSERT INTO reconciliation_participants
               (case_id, user_id, transaction_id, participant_role, participant_status)
               VALUES (%s, %s, %s, %s, %s)""",
            (case_id, user_id, transaction_id, participant_role, participant_status),
        )
        participant_id = cursor.lastrowid
        _insert_audit(cursor, case_id, "participant_added", "Transaction added to reconciliation case.",
                      {"transaction_id": transaction_id, "participant_id": participant_id}, "user", user_id)
        cursor.execute("UPDATE reconciliation_cases SET updated_at = CURRENT_TIMESTAMP WHERE case_id = %s", (case_id,))
        connection.commit()
        return {"success": True, "message": "Participant added successfully.", "participant_id": participant_id}
    except (Error, ValueError, TypeError) as error:
        if connection is not None:
            connection.rollback()
        return {"success": False, "message": str(error), "participant_id": None}
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


def add_case_evidence(user_id: int, case_id: int, evidence_type: str,
                      evidence_description: str = None, evidence_data=None, document_id: int = None):
    connection = cursor = None
    try:
        user_id = _positive_id(user_id, "user_id")
        case_id = _positive_id(case_id, "case_id")
        if evidence_type not in VALID_EVIDENCE_TYPES:
            raise ValueError("Invalid evidence_type.")
        connection = get_db_connection()
        if connection is None:
            return {"success": False, "message": "Could not connect to MySQL.", "evidence_id": None}
        cursor = connection.cursor()
        owner = _case_owner_for_update(cursor, case_id)
        if owner is None or owner[0] != user_id:
            raise ValueError("Reconciliation case not found for this user.")
        if document_id is not None:
            document_id = _positive_id(document_id, "document_id")
            cursor.execute("SELECT document_id FROM documents WHERE document_id = %s AND user_id = %s",
                           (document_id, user_id))
            if cursor.fetchone() is None:
                raise ValueError("Evidence document not found for this user.")
        cursor.execute(
            """INSERT INTO reconciliation_evidence
               (case_id, evidence_type, evidence_description, evidence_data, document_id)
               VALUES (%s, %s, %s, %s, %s)""",
            (case_id, evidence_type, evidence_description, _json_value(evidence_data), document_id),
        )
        evidence_id = cursor.lastrowid
        _insert_audit(cursor, case_id, "evidence_added", "Evidence added to reconciliation case.",
                      {"evidence_id": evidence_id, "document_id": document_id}, "user", user_id)
        cursor.execute("UPDATE reconciliation_cases SET updated_at = CURRENT_TIMESTAMP WHERE case_id = %s", (case_id,))
        connection.commit()
        return {"success": True, "message": "Evidence added successfully.", "evidence_id": evidence_id}
    except (Error, ValueError, TypeError) as error:
        if connection is not None:
            connection.rollback()
        return {"success": False, "message": str(error), "evidence_id": None}
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


def record_audit_event(user_id: int, case_id: int, event_type: str,
                       event_description: str = None, event_data=None):
    connection = cursor = None
    try:
        user_id = _positive_id(user_id, "user_id")
        case_id = _positive_id(case_id, "case_id")
        if not isinstance(event_type, str) or not event_type.strip() or len(event_type) > 100:
            raise ValueError("event_type must contain 1 to 100 characters.")
        connection = get_db_connection()
        if connection is None:
            return {"success": False, "message": "Could not connect to MySQL.", "event_id": None}
        cursor = connection.cursor()
        owner = _case_owner_for_update(cursor, case_id)
        if owner is None or owner[0] != user_id:
            raise ValueError("Reconciliation case not found for this user.")
        event_id = _insert_audit(cursor, case_id, event_type.strip(), event_description,
                                 event_data, "user", user_id)
        cursor.execute("UPDATE reconciliation_cases SET updated_at = CURRENT_TIMESTAMP WHERE case_id = %s", (case_id,))
        connection.commit()
        return {"success": True, "message": "Audit event recorded successfully.", "event_id": event_id}
    except (Error, ValueError, TypeError) as error:
        if connection is not None:
            connection.rollback()
        return {"success": False, "message": str(error), "event_id": None}
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


def record_case_decision(user_id: int, case_id: int, decision_type: str,
                         decision_reason: str = None, confidence_score=None):
    """Record an owning user's confirmation, rejection, or reopening decision."""
    connection = cursor = None
    try:
        user_id = _positive_id(user_id, "user_id")
        case_id = _positive_id(case_id, "case_id")
        if decision_type not in {"user_confirmed", "rejected", "reopened"}:
            raise ValueError("User decisions must be user_confirmed, rejected, or reopened.")
        score = _confidence(confidence_score)
        status_map = {"user_confirmed": "confirmed", "rejected": "rejected", "reopened": "reopened"}
        connection = get_db_connection()
        if connection is None:
            return {"success": False, "message": "Could not connect to MySQL."}
        cursor = connection.cursor()
        row = _case_owner_for_update(cursor, case_id)
        if row is None or row[0] != user_id:
            raise ValueError("Reconciliation case not found for this user.")
        current_status = row[1]
        if decision_type == "reopened":
            if current_status not in {"confirmed", "rejected"}:
                raise ValueError("Only a confirmed or rejected case can be reopened.")
        elif current_status in {"confirmed", "rejected"}:
            raise ValueError("This case is closed. Reopen it before changing its decision.")
        new_status = status_map[decision_type]
        cursor.execute(
            """INSERT INTO reconciliation_decisions
               (case_id, decision_type, decision_reason, confidence_score, actor_type, actor_user_id)
               VALUES (%s, %s, %s, %s, 'user', %s)""",
            (case_id, decision_type, decision_reason, score, user_id),
        )
        cursor.execute("UPDATE reconciliation_cases SET case_status = %s, updated_at = CURRENT_TIMESTAMP WHERE case_id = %s AND user_id = %s",
                       (new_status, case_id, user_id))
        _insert_audit(cursor, case_id, "decision_recorded", "User recorded a reconciliation decision.",
                      {"decision_type": decision_type, "previous_status": current_status,
                       "new_status": new_status}, "user", user_id)
        connection.commit()
        return {"success": True, "message": "Decision recorded successfully.", "case_status": new_status}
    except (Error, ValueError, TypeError) as error:
        if connection is not None:
            connection.rollback()
        return {"success": False, "message": str(error)}
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


def _allocation_participant_transactions(cursor, case_id, user_id, from_id, to_id):
    cursor.execute(
        """SELECT participant_id, transaction_id
           FROM reconciliation_participants
           WHERE case_id = %s AND user_id = %s AND participant_id IN (%s, %s)
           ORDER BY transaction_id""",
        (case_id, user_id, from_id, to_id),
    )
    rows = cursor.fetchall()
    if len(rows) != 2:
        raise ValueError("Both allocation participants must belong to this user's case.")
    mapping = {row[0]: row[1] for row in rows}
    return mapping[from_id], mapping[to_id]


def _validate_and_lock_allocation(cursor, case_id, user_id, from_id, to_id,
                                  amount, currency, require_verified_currency=True):
    source_tx, target_tx = _allocation_participant_transactions(
        cursor, case_id, user_id, from_id, to_id
    )
    _lock_transaction_profiles(cursor, [source_tx, target_tx], user_id)
    source, target = _validate_allocation_pair(
        cursor, user_id, source_tx, target_tx, amount, currency, require_verified_currency
    )
    return source, target


def add_reconciliation_allocation(user_id: int, case_id: int,
                                  from_participant_id: int, to_participant_id: int,
                                  allocated_amount, currency: str = "INR",
                                  allocation_status: str = "proposed"):
    """Create an allocation. Confirmed allocations require verified account currencies."""
    connection = cursor = None
    try:
        user_id = _positive_id(user_id, "user_id")
        case_id = _positive_id(case_id, "case_id")
        from_participant_id = _positive_id(from_participant_id, "from_participant_id")
        to_participant_id = _positive_id(to_participant_id, "to_participant_id")
        amount = _money(allocated_amount, "allocated_amount")
        if amount <= 0:
            raise ValueError("allocated_amount must be greater than zero.")
        if allocation_status not in VALID_ALLOCATION_STATUSES:
            raise ValueError("Invalid allocation_status.")
        if not isinstance(currency, str) or len(currency) != 3 or not currency.isalpha():
            raise ValueError("currency must be a three-letter currency code.")
        currency = currency.upper()
        if from_participant_id == to_participant_id:
            raise ValueError("An allocation cannot connect a participant to itself.")

        connection = get_db_connection()
        if connection is None:
            return {"success": False, "message": "Could not connect to MySQL.", "allocation_id": None}
        cursor = connection.cursor()
        owner = _case_owner_for_update(cursor, case_id)
        if owner is None or owner[0] != user_id:
            raise ValueError("Reconciliation case not found for this user.")
        if owner[1] in {"confirmed", "rejected"}:
            raise ValueError("Cannot add allocations to a closed case. Reopen it first.")
        if allocation_status == "rejected":
            raise ValueError("Create an allocation as proposed or confirmed; reject it through update_allocation_status().")
        _validate_and_lock_allocation(
            cursor, case_id, user_id, from_participant_id, to_participant_id,
            amount, currency, require_verified_currency=(allocation_status == "confirmed"),
        )
        if allocation_status == "confirmed":
            source_tx, target_tx = _allocation_participant_transactions(
                cursor, case_id, user_id, from_participant_id, to_participant_id
            )
            source, target = _transaction_financial_profile(cursor, source_tx, user_id), _transaction_financial_profile(cursor, target_tx, user_id)
            if source["currency"] != target["currency"] or source["currency"] != currency:
                raise ValueError("Confirmed allocation currency must match both linked account currencies.")
        cursor.execute(
            """INSERT INTO reconciliation_allocations
               (case_id, from_participant_id, to_participant_id, allocated_amount, currency, allocation_status)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (case_id, from_participant_id, to_participant_id, amount, currency, allocation_status),
        )
        allocation_id = cursor.lastrowid
        _insert_audit(cursor, case_id, "allocation_created", "Reconciliation allocation created.",
                      {"allocation_id": allocation_id, "amount": str(amount),
                       "currency": currency, "status": allocation_status}, "user", user_id)
        cursor.execute("UPDATE reconciliation_cases SET updated_at = CURRENT_TIMESTAMP WHERE case_id = %s", (case_id,))
        connection.commit()
        return {"success": True, "message": "Allocation created successfully.", "allocation_id": allocation_id}
    except (Error, ValueError, TypeError) as error:
        if connection is not None:
            connection.rollback()
        return {"success": False, "message": str(error), "allocation_id": None}
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


def update_allocation_status(user_id: int, case_id: int, allocation_id: int,
                             new_status: str, decision_reason: str = None):
    """Confirm or reject a proposed allocation, recording an audit event.

    Confirmations lock the underlying transactions and re-check both amount
    caps and account currencies immediately before changing the status.
    """
    connection = cursor = None
    try:
        user_id = _positive_id(user_id, "user_id")
        case_id = _positive_id(case_id, "case_id")
        allocation_id = _positive_id(allocation_id, "allocation_id")
        if new_status not in {"confirmed", "rejected"}:
            raise ValueError("new_status must be confirmed or rejected.")
        connection = get_db_connection()
        if connection is None:
            return {"success": False, "message": "Could not connect to MySQL."}
        cursor = connection.cursor()
        owner = _case_owner_for_update(cursor, case_id)
        if owner is None or owner[0] != user_id:
            raise ValueError("Reconciliation case not found for this user.")
        if owner[1] in {"confirmed", "rejected"}:
            raise ValueError("Cannot change allocations in a closed case. Reopen it first.")
        cursor.execute(
            """SELECT from_participant_id, to_participant_id, allocated_amount, currency, allocation_status
               FROM reconciliation_allocations
               WHERE allocation_id = %s AND case_id = %s FOR UPDATE""",
            (allocation_id, case_id),
        )
        row = cursor.fetchone()
        if row is None:
            raise ValueError("Allocation not found in this case.")
        from_id, to_id, amount_value, currency, current_status = row
        if current_status != "proposed":
            raise ValueError("Only proposed allocations can be confirmed or rejected.")
        if new_status == "confirmed":
            source, target = _validate_and_lock_allocation(
                cursor, case_id, user_id, from_id, to_id, _money(amount_value), currency,
                require_verified_currency=True,
            )
            if source["currency"] != target["currency"] or source["currency"] != currency:
                raise ValueError("Confirmed allocation currency must match both linked account currencies.")
        cursor.execute(
            "UPDATE reconciliation_allocations SET allocation_status = %s WHERE allocation_id = %s AND case_id = %s",
            (new_status, allocation_id, case_id),
        )
        _insert_audit(cursor, case_id, "allocation_status_changed",
                      "Reconciliation allocation status changed.",
                      {"allocation_id": allocation_id, "previous_status": current_status,
                       "new_status": new_status, "reason": decision_reason}, "user", user_id)
        cursor.execute("UPDATE reconciliation_cases SET updated_at = CURRENT_TIMESTAMP WHERE case_id = %s", (case_id,))
        connection.commit()
        return {"success": True, "message": "Allocation status updated successfully.", "allocation_status": new_status}
    except (Error, ValueError, TypeError) as error:
        if connection is not None:
            connection.rollback()
        return {"success": False, "message": str(error)}
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


def get_case_by_id(user_id: int, case_id: int):
    connection = cursor = None
    try:
        user_id = _positive_id(user_id, "user_id")
        case_id = _positive_id(case_id, "case_id")
        connection = get_db_connection()
        if connection is None:
            return {"success": False, "message": "Could not connect to MySQL.", "case": None}
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM reconciliation_cases WHERE case_id = %s AND user_id = %s", (case_id, user_id))
        case = cursor.fetchone()
        if case is None:
            return {"success": False, "message": "Reconciliation case not found.", "case": None}
        queries = {
            "participants": ("SELECT * FROM reconciliation_participants WHERE case_id = %s AND user_id = %s ORDER BY participant_id", (case_id, user_id)),
            "allocations": ("SELECT ra.* FROM reconciliation_allocations ra JOIN reconciliation_cases rc ON rc.case_id = ra.case_id WHERE ra.case_id = %s AND rc.user_id = %s ORDER BY ra.allocation_id", (case_id, user_id)),
            "evidence": ("SELECT re.* FROM reconciliation_evidence re JOIN reconciliation_cases rc ON rc.case_id = re.case_id WHERE re.case_id = %s AND rc.user_id = %s ORDER BY re.evidence_id", (case_id, user_id)),
            "decisions": ("SELECT rd.* FROM reconciliation_decisions rd JOIN reconciliation_cases rc ON rc.case_id = rd.case_id WHERE rd.case_id = %s AND rc.user_id = %s ORDER BY rd.decision_id", (case_id, user_id)),
            "audit_events": ("SELECT rae.* FROM reconciliation_audit_events rae JOIN reconciliation_cases rc ON rc.case_id = rae.case_id WHERE rae.case_id = %s AND rc.user_id = %s ORDER BY rae.event_id", (case_id, user_id)),
        }
        for key, (query, params) in queries.items():
            cursor.execute(query, params)
            case[key] = cursor.fetchall()
        return {"success": True, "message": "Reconciliation case retrieved successfully.", "case": case}
    except (Error, ValueError, TypeError) as error:
        return {"success": False, "message": str(error), "case": None}
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


def list_user_cases(user_id: int, limit: int = 50, offset: int = 0,
                    case_status: str = None, case_type: str = None):
    connection = cursor = None
    try:
        user_id = _positive_id(user_id, "user_id")
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 500:
            raise ValueError("limit must be between 1 and 500.")
        if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
            raise ValueError("offset must be a non-negative integer.")
        if case_status is not None and case_status not in VALID_CASE_STATUSES:
            raise ValueError("Invalid case_status.")
        if case_type is not None and case_type not in VALID_CASE_TYPES:
            raise ValueError("Invalid case_type.")
        connection = get_db_connection()
        if connection is None:
            return {"success": False, "message": "Could not connect to MySQL.", "count": 0, "cases": []}
        cursor = connection.cursor(dictionary=True)
        query = "SELECT * FROM reconciliation_cases WHERE user_id = %s"
        params = [user_id]
        if case_status is not None:
            query += " AND case_status = %s"
            params.append(case_status)
        if case_type is not None:
            query += " AND case_type = %s"
            params.append(case_type)
        query += " ORDER BY updated_at DESC, case_id DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        return {"success": True, "message": "Reconciliation cases retrieved successfully.",
                "count": len(rows), "cases": rows}
    except (Error, ValueError, TypeError) as error:
        return {"success": False, "message": str(error), "count": 0, "cases": []}
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()
