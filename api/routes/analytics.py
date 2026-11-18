
from fastapi import APIRouter, Depends, HTTPException, status

from api.auth_dependencies import get_current_user
from mysql_pipeline.analytics_storage import (
    get_financial_summary,
    get_monthly_trends,
    get_latest_account_balances,
    get_unlinked_transaction_summary,
)

router = APIRouter()


def handle_result(result, key):
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to retrieve financial analytics.",
        )

    return {
        "success": True,
        key: result[key],
    }


@router.get("/analytics/summary")
def financial_summary(
    user_id: int = Depends(get_current_user),
):
    result = get_financial_summary(user_id)

    response = handle_result(result, "summary")
    response["user_id"] = user_id

    return response


@router.get("/analytics/monthly")
def monthly_trends(
    user_id: int = Depends(get_current_user),
):
    result = get_monthly_trends(user_id)

    response = handle_result(result, "monthly_trends")
    response["user_id"] = user_id

    return response


@router.get("/analytics/account-balances")
def account_balances(
    user_id: int = Depends(get_current_user),
):
    result = get_latest_account_balances(user_id)

    response = handle_result(result, "account_balances")
    response["user_id"] = user_id

    return response


@router.get("/analytics/unlinked")
def unlinked_transactions(
    user_id: int = Depends(get_current_user),
):
    result = get_unlinked_transaction_summary(user_id)

    response = handle_result(result, "unlinked_summary")
    response["user_id"] = user_id

    return response
