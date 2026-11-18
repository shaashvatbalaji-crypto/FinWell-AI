
from mysql_pipeline.merchant_mapping_storage import (
    save_merchant_mapping
)

from reconciliation.merchant_normalizer import normalize_merchant


def test_save_merchant_mapping():

    description = "TEST PAYMENT UNKNOWN STORE 123"

    result = save_merchant_mapping(
        user_id=1,
        original_description=description,
        normalized_merchant="Test Store",
        category="Shopping"
    )

    print("Save result:", result)

    assert result["success"] is True

    # Verify that the normalizer reads the saved mapping.
    normalized = normalize_merchant(
        user_id=1,
        description=description
    )

    print("Normalization result:", normalized)

    assert normalized["normalized_merchant"] == "Test Store"
    assert normalized["category"] == "Shopping"
    assert normalized["method"] == "user_mapping"


if __name__ == "__main__":
    test_save_merchant_mapping()
