
from unittest.mock import MagicMock, patch

from reconciliation.merchant_normalizer import normalize_merchant


def test_legacy_string_interface():
    assert normalize_merchant(
        "POS PURCHASE FRESHBASKET MART CHENNAI"
    ) == "FRESHBASKET MART"

    assert normalize_merchant(
        "UPI QUICKBITE FOODS DINNER"
    ) == "QUICKBITE FOODS"

    assert normalize_merchant(
        "UNKNOWN TRANSACTION XYZ"
    ) is None


def test_custom_alias():
    result = normalize_merchant(
        "PAYMENT TEST STORE",
        merchant_aliases={
            "TEST MERCHANT": ["TEST STORE"]
        }
    )

    assert result == "TEST MERCHANT"


@patch("reconciliation.merchant_normalizer.get_db_connection")
def test_user_mapping_priority(mock_connection):
    connection = MagicMock()
    cursor = MagicMock()

    mock_connection.return_value = connection
    connection.cursor.return_value = cursor

    cursor.fetchone.return_value = (
        "My Preferred Store",
        "Shopping"
    )

    result = normalize_merchant(
        user_id=1,
        description="TEST PAYMENT UNKNOWN STORE"
    )

    assert result["success"] is True
    assert result["normalized_merchant"] == "My Preferred Store"
    assert result["category"] == "Shopping"
    assert result["method"] == "user_mapping"

    connection.commit.assert_not_called()
    cursor.execute.assert_called_once()


@patch("reconciliation.merchant_normalizer.get_db_connection")
def test_default_alias_fallback(mock_connection):
    connection = MagicMock()
    cursor = MagicMock()

    mock_connection.return_value = connection
    connection.cursor.return_value = cursor

    cursor.fetchone.return_value = None

    result = normalize_merchant(
        user_id=1,
        description="POS PURCHASE FRESH BASKET MART"
    )

    assert result["success"] is True
    assert result["normalized_merchant"] == "FRESHBASKET MART"
    assert result["method"] == "default_alias"


@patch("reconciliation.merchant_normalizer.get_db_connection")
def test_unknown_merchant(mock_connection):
    connection = MagicMock()
    cursor = MagicMock()

    mock_connection.return_value = connection
    connection.cursor.return_value = cursor

    cursor.fetchone.return_value = None

    result = normalize_merchant(
        user_id=1,
        description="UNKNOWN PAYMENT XYZ"
    )

    assert result["success"] is True
    assert result["normalized_merchant"] is None
    assert result["method"] == "unknown"


@patch("reconciliation.merchant_normalizer.get_db_connection")
def test_database_failure_falls_back_to_alias(mock_connection):
    mock_connection.side_effect = Exception("Database unavailable")

    result = normalize_merchant(
        user_id=1,
        description="FRESHBASKET MART CHENNAI"
    )

    assert result["success"] is True
    assert result["normalized_merchant"] == "FRESHBASKET MART"
    assert result["method"] == "default_alias"
    assert "lookup_warning" in result


if __name__ == "__main__":
    test_legacy_string_interface()
    test_custom_alias()
    test_user_mapping_priority()
    test_default_alias_fallback()
    test_unknown_merchant()
    test_database_failure_falls_back_to_alias()

    print("All merchant normalizer V1 tests passed.")
