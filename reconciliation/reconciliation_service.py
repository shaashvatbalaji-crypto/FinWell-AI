
from reconciliation.merchant_normalizer import normalize_merchant
from reconciliation.transaction_classifier import classify_transaction


def reconcile_transaction(
    user_id,
    description,
    debit=0,
    credit=0
):
    """
    Combine merchant normalization and transaction classification.

    This function analyses a transaction but does not modify
    the original transaction record or save reconciliation results.
    """

    merchant_result = normalize_merchant(
        user_id=user_id,
        description=description
    )

    if not merchant_result["success"]:
        return {
            "success": False,
            "message": "Merchant normalization failed.",
            "merchant_result": merchant_result
        }

    classification_result = classify_transaction(
        description=description,
        debit=debit,
        credit=credit,
        normalized_merchant=merchant_result["normalized_merchant"]
    )

    if not classification_result["success"]:
        return {
            "success": False,
            "message": "Transaction classification failed.",
            "merchant_result": merchant_result,
            "classification_result": classification_result
        }

    return {
        "success": True,
        "original_description": description,
        "normalized_merchant": merchant_result["normalized_merchant"],
        "merchant_method": merchant_result["method"],
        "transaction_type": classification_result["transaction_type"],
        "category": (
            merchant_result["category"]
            or classification_result["category"]
        ),
        "confidence_score": classification_result["confidence_score"],
        "classification_reason": classification_result["reason"]
    }
