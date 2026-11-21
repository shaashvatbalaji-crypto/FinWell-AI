
"""
FinWell AI - Unified Structured Retrieval Service

Purpose:
    Provide one unified interface for retrieving structured financial
    information from the existing MySQL storage modules.

Integrated modules:
    1. Transactions
    2. Financial Analytics
    3. Accounts
    4. Loans
    5. Investments
    6. Reconciliation

Design principles:
    - MySQL remains the source of truth.
    - All retrieval is scoped to the supplied user_id.
    - Existing storage implementations are not modified.
    - Original storage responses are preserved.
    - Individual section failures do not prevent other sections
      from being retrieved.
"""

from mysql_pipeline.transaction_storage import (
    list_user_transactions,
)

from mysql_pipeline.analytics_storage import (
    get_financial_summary,
    get_monthly_trends,
    get_latest_account_balances,
    get_unlinked_transaction_summary,
)

from mysql_pipeline.account_storage import (
    list_user_accounts,
)

from mysql_pipeline.loan_storage import (
    list_user_loans,
)

from mysql_pipeline.investment_storage import (
    list_user_investments,
)

from mysql_pipeline.reconciliation_storage import (
    list_pending_matches,
)

from mysql_pipeline.reconciliation_case_storage import (
    list_user_cases,
)


# ============================================================
# CONFIGURATION
# ============================================================

AVAILABLE_SECTIONS = {
    "transactions",
    "analytics",
    "accounts",
    "loans",
    "investments",
    "reconciliation",
}

DEFAULT_TRANSACTION_LIMIT = 100
DEFAULT_RECONCILIATION_LIMIT = 100
DEFAULT_CASE_LIMIT = 50
MAX_RETRIEVAL_LIMIT = 500


# ============================================================
# VALIDATION
# ============================================================

def _validate_positive_id(value, field_name):
    """Validate a positive integer identifier."""

    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value <= 0
    ):
        raise ValueError(
            f"{field_name} must be a positive integer."
        )


def _validate_pagination(limit, offset, max_limit=MAX_RETRIEVAL_LIMIT):
    """Validate pagination parameters."""

    if isinstance(limit, bool) or not isinstance(limit, int):
        raise ValueError("limit must be an integer.")

    if not 1 <= limit <= max_limit:
        raise ValueError(
            f"limit must be between 1 and {max_limit}."
        )

    if (
        isinstance(offset, bool)
        or not isinstance(offset, int)
        or offset < 0
    ):
        raise ValueError(
            "offset must be a non-negative integer."
        )


def _validate_sections(include):
    """Validate and normalize requested sections."""

    if include is None:
        return set(AVAILABLE_SECTIONS)

    if isinstance(include, str):
        raise ValueError(
            "include must be a list, tuple or set of sections."
        )

    if not isinstance(include, (list, tuple, set)):
        raise ValueError(
            "include must be a list, tuple or set of sections."
        )

    if not all(isinstance(section, str) for section in include):
        raise ValueError(
            "Every section name must be a string."
        )

    selected = set(include)

    unknown_sections = selected - AVAILABLE_SECTIONS

    if unknown_sections:
        raise ValueError(
            f"Unknown retrieval sections: "
            f"{sorted(unknown_sections)}"
        )

    return selected


# ============================================================
# ANALYTICS RETRIEVAL
# ============================================================

def _get_analytics(user_id):
    """
    Retrieve all structured financial analytics.

    Each analytics function is called exactly once.
    """

    summary = get_financial_summary(user_id)

    trends = get_monthly_trends(user_id)

    balances = get_latest_account_balances(user_id)

    unlinked = get_unlinked_transaction_summary(user_id)

    analytics_success = all(
        isinstance(result, dict)
        and result.get("success", False)
        for result in (
            summary,
            trends,
            balances,
            unlinked,
        )
    )

    return {
        "success": analytics_success,

        "financial_summary": summary,

        "monthly_trends": trends,

        "account_balances": balances,

        "unlinked_transactions": unlinked,
    }


# ============================================================
# RECONCILIATION RETRIEVAL
# ============================================================

def _get_reconciliation(
    user_id,
    reconciliation_limit,
    case_limit,
    case_offset,
    case_status,
    case_type,
):
    """
    Retrieve pending reconciliation matches and reconciliation cases.
    """

    pending_matches = list_pending_matches(
        user_id,
        limit=reconciliation_limit,
    )

    cases = list_user_cases(
        user_id,
        limit=case_limit,
        offset=case_offset,
        case_status=case_status,
        case_type=case_type,
    )

    reconciliation_success = all(
        isinstance(result, dict)
        and result.get("success", False)
        for result in (
            pending_matches,
            cases,
        )
    )

    return {
        "success": reconciliation_success,

        "pending_matches": pending_matches,

        "cases": cases,
    }


# ============================================================
# SECTION EXECUTION
# ============================================================

def _execute_section(section_name, operation, results, statuses):
    """
    Execute one retrieval section safely.

    A failure in one section does not stop other sections.
    """

    try:
        result = operation()

        if not isinstance(result, dict):
            raise TypeError(
                f"{section_name} returned an unexpected response type."
            )

        success = bool(result.get("success", False))

        results[section_name] = result

        statuses[section_name] = success

    except Exception as error:

        results[section_name] = {
            "success": False,
            "message": (
                f"{section_name} retrieval failed: {error}"
            ),
        }

        statuses[section_name] = False


# ============================================================
# MAIN STRUCTURED RETRIEVAL SERVICE
# ============================================================

def get_structured_financial_data(
    user_id,
    include=None,
    transaction_limit=DEFAULT_TRANSACTION_LIMIT,
    transaction_offset=0,
    reconciliation_limit=DEFAULT_RECONCILIATION_LIMIT,
    case_limit=DEFAULT_CASE_LIMIT,
    case_offset=0,
    case_status=None,
    case_type=None,
):
    """
    Unified entry point for structured financial retrieval.

    Args:
        user_id (int):
            Internal database user ID.

        include (list, tuple, set, optional):
            Sections to retrieve.

            Available sections:
                transactions
                analytics
                accounts
                loans
                investments
                reconciliation

            If None, all sections are retrieved.

        transaction_limit (int):
            Maximum transactions to retrieve.

        transaction_offset (int):
            Transaction pagination offset.

        reconciliation_limit (int):
            Maximum pending reconciliation matches.

        case_limit (int):
            Maximum reconciliation cases.

        case_offset (int):
            Reconciliation case pagination offset.

        case_status (str, optional):
            Filter reconciliation cases by status.

        case_type (str, optional):
            Filter reconciliation cases by type.

    Returns:
        dict:
            {
                "success": True,
                "user_id": 1,
                "sections_requested": [...],
                "section_status": {...},
                "data": {...}
            }

    Notes:
        The user_id must come from a trusted, authenticated
        application context. Do not accept an arbitrary user_id
        directly from an untrusted client request.
    """

    # --------------------------------------------------------
    # 1. Validate request
    # --------------------------------------------------------

    _validate_positive_id(user_id, "user_id")

    _validate_pagination(
        transaction_limit,
        transaction_offset,
    )

    _validate_pagination(
        reconciliation_limit,
        0,
    )

    _validate_pagination(
        case_limit,
        case_offset,
    )

    selected_sections = _validate_sections(include)

    # --------------------------------------------------------
    # 2. Initialize response
    # --------------------------------------------------------

    results = {}

    section_status = {}

    # --------------------------------------------------------
    # 3. Define retrieval operations
    # --------------------------------------------------------

    operations = {

        "transactions": lambda: list_user_transactions(
            user_id,
            limit=transaction_limit,
            offset=transaction_offset,
        ),

        "analytics": lambda: _get_analytics(
            user_id
        ),

        "accounts": lambda: list_user_accounts(
            user_id
        ),

        "loans": lambda: list_user_loans(
            user_id
        ),

        "investments": lambda: list_user_investments(
            user_id
        ),

        "reconciliation": lambda: _get_reconciliation(
            user_id=user_id,
            reconciliation_limit=reconciliation_limit,
            case_limit=case_limit,
            case_offset=case_offset,
            case_status=case_status,
            case_type=case_type,
        ),
    }

    # --------------------------------------------------------
    # 4. Execute requested sections
    # --------------------------------------------------------

    for section in AVAILABLE_SECTIONS:

        if section not in selected_sections:
            continue

        _execute_section(
            section_name=section,
            operation=operations[section],
            results=results,
            statuses=section_status,
        )

    # --------------------------------------------------------
    # 5. Determine overall status
    # --------------------------------------------------------

    overall_success = (
        all(section_status.values())
        if section_status
        else True
    )

    # --------------------------------------------------------
    # 6. Return unified response
    # --------------------------------------------------------

    return {
        "success": overall_success,

        "user_id": user_id,

        "sections_requested": sorted(
            selected_sections
        ),

        "section_status": section_status,

        "data": results,
    }


# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================

def get_financial_overview(user_id):
    """
    Retrieve a compact financial overview.

    Includes:
        - Analytics
        - Accounts
        - Loans
        - Investments
    """

    return get_structured_financial_data(
        user_id=user_id,
        include=[
            "analytics",
            "accounts",
            "loans",
            "investments",
        ],
    )


def get_transaction_overview(
    user_id,
    limit=DEFAULT_TRANSACTION_LIMIT,
    offset=0,
):
    """
    Retrieve transactions and financial analytics.
    """

    return get_structured_financial_data(
        user_id=user_id,
        include=[
            "transactions",
            "analytics",
        ],
        transaction_limit=limit,
        transaction_offset=offset,
    )


def get_reconciliation_overview(
    user_id,
    limit=DEFAULT_RECONCILIATION_LIMIT,
):
    """
    Retrieve pending reconciliation matches and cases.
    """

    return get_structured_financial_data(
        user_id=user_id,
        include=[
            "reconciliation",
        ],
        reconciliation_limit=limit,
    )


# ============================================================
# MODULE TEST
# ============================================================

if __name__ == "__main__":

    import json

    print("=" * 65)
    print("FINWELL AI - STRUCTURED RETRIEVAL SERVICE")
    print("=" * 65)

    print(
        "\nThis module provides unified structured retrieval."
    )

    print(
        "\nAvailable sections:"
    )

    for section in sorted(AVAILABLE_SECTIONS):
        print(f"  - {section}")

    print(
        "\nImport get_structured_financial_data() "
        "from your application."
    )

    print(
        "\nNo database query is executed by this module test."
    )
