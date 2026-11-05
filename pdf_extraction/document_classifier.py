import re


DOCUMENT_KEYWORDS = {
    "bank_statement": [
        "bank statement",
        "account statement",
        "opening balance",
        "closing balance",
        "available balance",
        "account number",
        "transaction date",
    ],
    "credit_card_statement": [
        "credit card statement",
        "card statement",
        "minimum amount due",
        "total amount due",
        "credit limit",
        "statement balance",
    ],
    "loan_agreement": [
        "loan agreement",
        "loan amount",
        "principal amount",
        "interest rate",
        "repayment schedule",
        "emi",
        "equated monthly instalment",
        "equated monthly installment",
    ],
    "insurance_policy": [
        "insurance policy",
        "policy number",
        "sum insured",
        "premium amount",
        "policyholder",
        "coverage period",
        "insurance coverage",
    ],
    "investment_statement": [
        "investment statement",
        "portfolio statement",
        "mutual fund",
        "shares held",
        "units held",
        "net asset value",
        "demat account",
    ],
}


def classify_document(text: str) -> dict:
    """
    Classify a financial document using keyword matching.

    Args:
        text: Text extracted from a PDF.

    Returns:
        Predicted document type, matched keywords, and confidence score.
    """

    if not text or not text.strip():
        return {
            "success": False,
            "document_type": "unknown",
            "confidence": 0.0,
            "matched_keywords": [],
            "error": "No text was provided for classification.",
        }

    normalized_text = re.sub(r"\s+", " ", text.lower())

    scores = {}
    matched_keywords_by_type = {}

    for document_type, keywords in DOCUMENT_KEYWORDS.items():
        matched_keywords = [
            keyword
            for keyword in keywords
            if keyword in normalized_text
        ]

        scores[document_type] = len(matched_keywords)
        matched_keywords_by_type[document_type] = matched_keywords

    best_type = max(scores, key=scores.get)
    best_score = scores[best_type]

    if best_score == 0:
        return {
            "success": True,
            "document_type": "unknown",
            "confidence": 0.0,
            "matched_keywords": [],
            "error": None,
        }

    total_keywords = len(DOCUMENT_KEYWORDS[best_type])
    confidence = min(best_score / total_keywords, 1.0)

    return {
        "success": True,
        "document_type": best_type,
        "confidence": round(confidence, 2),
        "matched_keywords": matched_keywords_by_type[best_type],
        "error": None,
    }