"""Authenticated reconciliation endpoints for FinWell AI."""
from typing import Literal, Optional
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from api.auth_dependencies import get_current_user
from mysql_pipeline.reconciliation_storage import (
    list_pending_matches,
    update_match_status,
)
from reconciliation.unified_reconciliation_service import (
    reconcile_user_from_database,
)

router = APIRouter(prefix="/reconciliation", tags=["Reconciliation"])


class MatchStatusUpdateRequest(BaseModel):
    status: Literal["confirmed", "rejected"]


def _format_confidence(score: Optional[Decimal]) -> Optional[float]:
    if score is None:
        return None
    return float(round(Decimal(str(score)) * 100, 2))


@router.get("/cases")
def get_reconciliation_cases(
    limit: int = Query(default=100, ge=1, le=500),
    user_id: int = Depends(get_current_user),
):
    """
    Retrieve pending reconciliation suggestions for the authenticated user.
    Enforces strict user isolation.
    """
    try:
        from services.ingestion_service import _auto_discover_reconciliation_matches
        _auto_discover_reconciliation_matches(user_id)
    except Exception:
        pass

    result = list_pending_matches(user_id=user_id, limit=limit)

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=result.get("message", "Unable to retrieve reconciliation matches."),
        )

    cases = []
    for m in result.get("matches", []):
        confidence = _format_confidence(m.get("confidence_score"))

        # Source leg
        s_debit = float(m["first_debit"]) if m["first_debit"] is not None else None
        s_credit = float(m["first_credit"]) if m["first_credit"] is not None else None
        s_is_credit = s_credit is not None and s_credit > 0
        s_amount = s_credit if s_is_credit else (s_debit or 0.0)

        # Target leg
        t_debit = float(m["second_debit"]) if m["second_debit"] is not None else None
        t_credit = float(m["second_credit"]) if m["second_credit"] is not None else None
        t_is_credit = t_credit is not None and t_credit > 0
        t_amount = t_credit if t_is_credit else (t_debit or 0.0)

        case_type = m.get("match_type", "internal_transfer")
        if case_type == "duplicate":
            title = f"Duplicate Transaction Review #{m['match_id']}"
        elif case_type == "refund":
            title = f"Refund Allocation Review #{m['match_id']}"
        else:
            title = f"Internal Transfer Review #{m['match_id']}"

        cases.append({
            "case_id": m["match_id"],
            "case_type": case_type,
            "status": m["match_status"],
            "confidence_score": confidence,
            "title": title,
            "description": m.get("match_reason") or "Suggested reconciliation match requiring confirmation.",
            "created_at": str(m.get("created_at") or m["first_date"]),
            "source_transaction": {
                "transaction_id": m["transaction_id"],
                "account_id": m.get("first_account_id"),
                "account_name": m.get("first_account_name"),
                "transaction_date": str(m["first_date"]),
                "description": m["first_description"],
                "category": "Reconciliation Review",
                "debit": s_debit,
                "credit": s_credit,
                "amount": s_amount,
                "direction": "credit" if s_is_credit else "debit",
                "currency": m.get("first_currency"),
                "status": "posted",
            },
            "target_transaction": {
                "transaction_id": m["matched_transaction_id"],
                "account_id": m.get("second_account_id"),
                "account_name": m.get("second_account_name"),
                "transaction_date": str(m["second_date"]),
                "description": m["second_description"],
                "category": "Reconciliation Review",
                "debit": t_debit,
                "credit": t_credit,
                "amount": t_amount,
                "direction": "credit" if t_is_credit else "debit",
                "currency": m.get("second_currency"),
                "status": "posted",
            },
            "evidences": [
                {
                    "evidence_type": "transaction_reference",
                    "description": m.get("match_reason") or "Reconciliation engine heuristic alignment.",
                    "score": confidence,
                }
            ],
        })

    return {
        "success": True,
        "user_id": user_id,
        "count": len(cases),
        "cases": cases,
    }


@router.patch("/cases/{case_id}/status")
def review_reconciliation_match(
    case_id: int,
    request: MatchStatusUpdateRequest,
    user_id: int = Depends(get_current_user),
):
    """
    Confirm or reject a specific suggested match.
    Only the selected match is updated. Unrelated matches remain untouched.
    """
    result = update_match_status(
        user_id=user_id,
        match_id=case_id,
        new_status=request.status,
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("message", "Unable to update match status."),
        )

    return {
        "success": True,
        "match_id": case_id,
        "new_status": request.status,
        "message": result.get("message"),
    }


@router.post("/evaluate")
def evaluate_reconciliation_dry_run(
    user_id: int = Depends(get_current_user),
):
    """
    Read-only heuristic evaluation across the authenticated user's transactions.
    DRY RUN:
    - Does NOT modify database records.
    - Does NOT automatically confirm or reject matches.
    """
    try:
        from services.ingestion_service import _auto_discover_reconciliation_matches
        _auto_discover_reconciliation_matches(user_id)
    except Exception:
        pass

    result = reconcile_user_from_database(user_id=user_id)
    return result
