
from fastapi import APIRouter, Depends, HTTPException, Query

from api.auth_dependencies import get_current_user
from mysql_pipeline.transaction_storage import (
    list_user_transactions,
    list_document_transactions,
)

router = APIRouter()


@router.get("/transactions")
def get_transactions(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    user_id: int = Depends(get_current_user),
):
    result = list_user_transactions(
        user_id=user_id,
        limit=limit,
        offset=offset,
    )

    if not result["success"]:
        raise HTTPException(
            status_code=503,
            detail="Unable to retrieve transactions.",
        )

    return {
        "success": True,
        "message": "Transactions retrieved successfully.",
        "user_id": user_id,
        "count": result["count"],
        "transactions": result["transactions"],
    }


@router.get("/transactions/document/{document_id}")
def get_document_transactions(
    document_id: int,
    user_id: int = Depends(get_current_user),
):
    result = list_document_transactions(
        document_id=document_id,
        user_id=user_id,
    )

    if not result["success"]:
        raise HTTPException(
            status_code=503,
            detail="Unable to retrieve document transactions.",
        )

    return {
        "success": True,
        "message": "Document transactions retrieved successfully.",
        "user_id": user_id,
        "document_id": document_id,
        "count": result["count"],
        "transactions": result["transactions"],
    }
