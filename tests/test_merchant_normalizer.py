
from reconciliation.merchant_normalizer import normalize_merchant


def test_merchant_normalization():

    test_descriptions = [
        "POS PURCHASE FRESHBASKET MART CHENNAI",
        "POS PURCHASE FRESH BASKET MART CHENNAI",
        "UPI/DR/627233451892/QUICKBITE FOODS/DINNER ORDER",
        "UPI/DR/627955012233/URBANCAB RIDES/TRIP",
        "ATM CASH WDL 000231 MCB ATM ADYAR",
        "TRF TO SELF A/C XXXX7788 GOAL SAVINGS REF ITR-1009",
        "UNKNOWN TRANSACTION XYZ"
    ]

    for description in test_descriptions:

        result = normalize_merchant(
            user_id=1,
            description=description
        )

        print("\nOriginal:", description)
        print("Normalized:", result["normalized_merchant"])
        print("Method:", result["method"])

        assert result["success"] is True


if __name__ == "__main__":
    test_merchant_normalization()
