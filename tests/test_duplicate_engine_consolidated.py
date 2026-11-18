
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from reconciliation.duplicate_detector import detect_duplicate_candidate
from reconciliation.transaction_features import extract_transaction_features
from reconciliation.reference_extractor import extract_reference
from reconciliation.merchant_normalizer import normalize_merchant


passed = 0
failed = 0


def check(name, condition, details=""):
    global passed, failed

    if condition:
        passed += 1
        print(f"PASS: {name}")
    else:
        failed += 1
        print(f"FAIL: {name}")
        if details:
            print(f"      {details}")


def transaction(
    transaction_id,
    document_id,
    account_id="ACCOUNT_4821",
    reference="A501",
    date="2026-11-12",
    amount=1250.00,
    direction="debit",
    user_id=999999,
    currency="INR",
    description=None,
):
    if description is None:
        description = (
            f"UPI FRESH BASKET MART REF {reference}"
            if reference else "UPI FRESH BASKET MART"
        )

    return {
        "transaction_id": transaction_id,
        "document_id": document_id,
        "user_id": user_id,
        "account_id": account_id,
        "transaction_date": date,
        "description": description,
        "debit": amount if direction == "debit" else None,
        "credit": amount if direction == "credit" else None,
        "currency": currency,
    }


def main():
    print("=" * 65)
    print("FINWELL AI - CONSOLIDATED DUPLICATE ENGINE TEST")
    print("=" * 65)

    # 1. Genuine duplicate across documents.
    a = transaction(1, 100, reference="DUP501")
    b = transaction(2, 200, reference="DUP501")

    result = detect_duplicate_candidate(a, b)

    check(
        "Genuine duplicate across documents",
        result.get("is_candidate") is True,
        str(result),
    )

    # 2. Different explicit references.
    a = transaction(3, 100, reference="A501")
    b = transaction(4, 200, reference="A999")

    result = detect_duplicate_candidate(a, b)

    check(
        "Different explicit references rejected",
        result.get("is_candidate") is False
        and "references" in result.get("reason", "").lower(),
        str(result),
    )

    # 3. One missing reference.
    a = transaction(5, 100, reference="A501")
    b = transaction(6, 200, reference=None)

    result = detect_duplicate_candidate(a, b)

    check(
        "Missing reference treated as unknown",
        result.get("is_candidate") is True,
        str(result),
    )

    # 4. Different known accounts.
    a = transaction(7, 100, account_id="ACCOUNT_4821")
    b = transaction(8, 200, account_id="ACCOUNT_7392")

    result = detect_duplicate_candidate(a, b)

    check(
        "Different accounts rejected",
        result.get("is_candidate") is False
        and "accounts" in result.get("reason", "").lower(),
        str(result),
    )

    # 5. One missing account.
    a = transaction(9, 100, account_id="ACCOUNT_4821")
    b = transaction(10, 200, account_id=None)

    result = detect_duplicate_candidate(a, b)

    check(
        "Missing account treated as unknown",
        result.get("is_candidate") is True,
        str(result),
    )

    # 6. Currency mismatch.
    a = transaction(11, 100, currency="INR")
    b = transaction(12, 200, currency="USD")

    result = detect_duplicate_candidate(a, b)

    check(
        "Different currencies rejected",
        result.get("is_candidate") is False
        and "currencies" in result.get("reason", "").lower(),
        str(result),
    )

    # 7. Different users.
    a = transaction(13, 100, user_id=1)
    b = transaction(14, 200, user_id=2)

    result = detect_duplicate_candidate(a, b)

    check(
        "Different users rejected",
        result.get("is_candidate") is False,
        str(result),
    )

    # 8. Different transaction directions.
    a = transaction(15, 100, direction="debit")
    b = transaction(16, 200, direction="credit")

    result = detect_duplicate_candidate(a, b)

    check(
        "Different debit/credit directions rejected",
        result.get("is_candidate") is False,
        str(result),
    )

    # 9. Different dates beyond tolerance.
    a = transaction(17, 100, date="2026-11-01")
    b = transaction(18, 200, date="2026-11-10")

    result = detect_duplicate_candidate(a, b)

    check(
        "Dates beyond tolerance rejected",
        result.get("is_candidate") is False,
        str(result),
    )

    # 10. Merchant normalization.
    merchant = normalize_merchant(
        "UPI PAYMENT FRESH BASKET MART CHENNAI"
    )

    check(
        "Merchant alias normalization",
        merchant == "FRESHBASKET MART",
        str(merchant),
    )

    # 11. Reference extraction.
    reference = extract_reference(
        "UPI PAYMENT REF: A501"
    )

    check(
        "Reference extraction",
        reference == "A501",
        str(reference),
    )

    # 12. Feature extraction.
    features = extract_transaction_features(
        transaction(19, 100, reference="A501")
    )

    check(
        "Transaction feature extraction",
        features["amount"] == 1250
        and features["direction"] == "debit"
        and features["reference"] == "A501"
        and features["merchant"] == "FRESHBASKET MART",
        str(features),
    )

    # 13. Original transaction remains unchanged.
    original = transaction(20, 100, reference="A501")
    original_before = dict(original)

    extract_transaction_features(original)

    check(
        "Original transaction remains unchanged",
        original == original_before,
    )

    # 14. Malformed amount handled safely.
    a = transaction(21, 100)
    b = transaction(22, 200)
    a["debit"] = "NOT_AN_AMOUNT"

    result = detect_duplicate_candidate(a, b)

    check(
        "Malformed amount handled safely",
        result.get("is_candidate") is False,
        str(result),
    )

    # 15. Zero amount rejected.
    a = transaction(23, 100, amount=0)
    b = transaction(24, 200, amount=0)

    result = detect_duplicate_candidate(a, b)

    check(
        "Zero amount rejected",
        result.get("is_candidate") is False,
        str(result),
    )

    print("\n" + "=" * 65)
    print(f"TOTAL: {passed + failed}")
    print(f"PASSED: {passed}")
    print(f"FAILED: {failed}")
    print("=" * 65)

    if failed:
        raise SystemExit(1)

    print("FINAL STATUS: ALL CONSOLIDATED TESTS PASSED")


if __name__ == "__main__":
    main()
