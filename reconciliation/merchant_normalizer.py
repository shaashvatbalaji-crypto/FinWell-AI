
import re

from mysql_pipeline.db import get_db_connection


DEFAULT_MERCHANT_ALIASES = {
    "FRESHBASKET MART": [
        "FRESH BASKET MART",
        "FRESHBASKET",
        "FRESH BASKET",
    ],
    "QUICKBITE FOODS": [
        "QUICKBITE FOODS",
        "QUICKBITE",
    ],
    "URBANCAB RIDES": [
        "URBANCAB RIDES",
        "URBANCAB",
    ],
    "VELOCITY ELECTRONICS": [
        "VELOCITY ELECTRONICS",
        "VELOCITY",
    ],
    "SPICEROUTE RESTAURANT": [
        "SPICEROUTE RESTAURANT",
        "SPICEROUTE",
    ],
    "VOLTAMOBILE": [
        "VOLTAMOBILE",
        "VOLTA MOBILE",
    ],
}


def normalize_text(value):
    if not value:
        return ""

    value = str(value).upper()
    value = re.sub(r"[^A-Z0-9\s]", " ", value)
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def build_alias_index(merchant_aliases=None):
    """Build an alias-to-canonical-name mapping."""

    aliases = dict(DEFAULT_MERCHANT_ALIASES)

    if merchant_aliases:
        for canonical, values in merchant_aliases.items():
            aliases[canonical] = list(values)

    index = {}

    for canonical, names in aliases.items():
        canonical_name = normalize_text(canonical)

        if not canonical_name:
            continue

        index[canonical_name] = canonical_name

        for alias in names:
            normalized_alias = normalize_text(alias)

            if normalized_alias:
                index[normalized_alias] = canonical_name

    return index


def _match_default_merchant(description, merchant_aliases=None):
    """Match a known merchant alias without accessing MySQL."""

    text = normalize_text(description)

    if not text:
        return None

    alias_index = build_alias_index(merchant_aliases)

    for alias in sorted(alias_index, key=len, reverse=True):
        pattern = (
            r"(?<![A-Z0-9])"
            + re.escape(alias)
            + r"(?![A-Z0-9])"
        )

        if re.search(pattern, text):
            return alias_index[alias]

    return None


def _get_user_mapping(user_id, description):
    """
    Read a user-specific merchant mapping.

    This function is read-only. It never inserts or updates records.
    Returns (mapping, error).
    """

    connection = None
    cursor = None

    try:
        connection = get_db_connection()

        if connection is None:
            return None, "Could not connect to MySQL."

        cursor = connection.cursor()

        query = """
            SELECT normalized_merchant, category
            FROM merchant_mappings
            WHERE user_id = %s
              AND original_description = %s
            LIMIT 1
        """

        cursor.execute(
            query,
            (user_id, str(description).strip())
        )

        row = cursor.fetchone()

        if row:
            return {
                "normalized_merchant": row[0],
                "category": row[1],
            }, None

        return None, None

    except Exception as error:
        return None, str(error)

    finally:
        if cursor:
            cursor.close()

        if connection:
            try:
                if connection.is_connected():
                    connection.close()
            except Exception:
                pass


def normalize_merchant(
    description=None,
    merchant_aliases=None,
    user_id=None
):
    """
    Normalize a merchant.

    Backward compatibility:
      normalize_merchant(description)
          -> merchant string or None

      normalize_merchant(description, merchant_aliases=...)
          -> merchant string or None

    Structured result:
      normalize_merchant(user_id=1, description=...)
          -> dictionary containing success, normalized_merchant,
             category and method.

    Lookup priority:
      1. User-specific MySQL mapping
      2. Built-in/custom aliases
      3. Unknown merchant
    """

    # Preserve the existing string-returning interface.
    if user_id is None:
        return _match_default_merchant(
            description,
            merchant_aliases
        )

    if not isinstance(user_id, int) or user_id <= 0:
        return {
            "success": False,
            "normalized_merchant": None,
            "category": None,
            "method": "invalid_user",
            "message": "A valid user_id is required.",
        }

    if not description or not str(description).strip():
        return {
            "success": True,
            "normalized_merchant": None,
            "category": None,
            "method": "unknown",
            "message": "Transaction description is empty.",
        }

    # Priority 1: User-specific mapping.
    mapping, lookup_error = _get_user_mapping(
        user_id,
        description
    )

    if mapping:
        return {
            "success": True,
            "normalized_merchant": mapping["normalized_merchant"],
            "category": mapping["category"],
            "method": "user_mapping",
        }

    # Priority 2: Default or custom aliases.
    merchant = _match_default_merchant(
        description,
        merchant_aliases
    )

    if merchant:
        result = {
            "success": True,
            "normalized_merchant": merchant,
            "category": None,
            "method": "default_alias",
        }

        if lookup_error:
            result["lookup_warning"] = lookup_error

        return result

    # Priority 3: Unknown merchant.
    result = {
        "success": True,
        "normalized_merchant": None,
        "category": None,
        "method": "unknown",
    }

    if lookup_error:
        result["lookup_warning"] = lookup_error

    return result
