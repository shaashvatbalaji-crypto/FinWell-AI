
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from api.auth_dependencies import get_current_user
from mysql_pipeline.account_storage import (
    create_account,
    list_user_accounts,
    get_account_by_id,
)

router = APIRouter()


class AccountCreateRequest(BaseModel):
    account_name: str = Field(min_length=1)
    institution_name: Optional[str] = None
    account_type: Literal[
        "savings",
        "current",
        "salary",
        "credit_card",
        "loan",
        "investment",
        "cash",
        "other",
    ] = "other"
    masked_account_number: Optional[str] = None
    currency: str = Field(default="INR", pattern=r"^[A-Za-z]{3}$")


@router.get("/accounts")
def get_accounts(
    user_id: int = Depends(get_current_user),
):
    result = list_user_accounts(user_id)

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to retrieve accounts.",
        )

    return {
        "success": True,
        "user_id": user_id,
        "total_accounts": result["total_accounts"],
        "accounts": result["accounts"],
    }


@router.get("/accounts/{account_id}")
def get_account(
    account_id: int,
    user_id: int = Depends(get_current_user),
):
    result = get_account_by_id(user_id, account_id)

    if not result["success"]:
        if result.get("message") == "Account not found for this user.":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found.",
            )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to retrieve account.",
        )

    return {
        "success": True,
        "account": result["account"],
    }


@router.post("/accounts", status_code=status.HTTP_201_CREATED)
def add_account(
    request: AccountCreateRequest,
    user_id: int = Depends(get_current_user),
):
    result = create_account(
        user_id=user_id,
        account_name=request.account_name.strip(),
        institution_name=request.institution_name,
        account_type=request.account_type,
        masked_account_number=request.masked_account_number,
        currency=request.currency,
    )

    if not result["success"]:
        if "required" in result["message"].lower() or "invalid" in result["message"].lower():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=result["message"],
            )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to create account.",
        )

    return {
        "success": True,
        "message": "Account created successfully.",
        "user_id": user_id,
        "account_id": result["account_id"],
    }
