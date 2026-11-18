import os
import requests
import pandas as pd
import streamlit as st
from datetime import datetime

# ============================================================
# FinWell AI — Streamlit Frontend
# ============================================================

API_BASE_URL = os.getenv("FINWELL_API_URL", "http://127.0.0.1:8001")
MAX_FILE_SIZE_MB = 20

st.set_page_config(
    page_title="FinWell AI",
    page_icon="💠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ------------------------- Styling ---------------------------

st.markdown(
    """
    <style>
        /* App surfaces */
        .stApp,
        [data-testid="stAppViewContainer"] {
            background: #F5F7FB !important;
            color: #101828 !important;
        }

        [data-testid="stHeader"] {
            background: #F5F7FB !important;
        }

        /* Sidebar */
        section[data-testid="stSidebar"] {
            background: #101828 !important;
        }
        section[data-testid="stSidebar"] * {
            color: #F2F4F7 !important;
        }

        /* Main content typography: explicitly override inherited theme colors */
        .main .block-container,
        .main .block-container p,
        .main .block-container span,
        .main .block-container label,
        .main .block-container h1,
        .main .block-container h2,
        .main .block-container h3,
        .main .block-container h4,
        .main .block-container [data-testid="stMarkdownContainer"] {
            color: #101828;
        }

        .main-title {
            font-size: 2.1rem;
            font-weight: 750;
            color: #101828 !important;
            margin-bottom: 0;
        }
        .subtitle {
            color: #475467 !important;
            margin-top: 0.2rem;
            margin-bottom: 1.4rem;
        }

        /* Metrics */
        div[data-testid="stMetric"] {
            background: #FFFFFF !important;
            border: 1px solid #EAECF0;
            padding: 18px;
            border-radius: 14px;
        }
        div[data-testid="stMetricLabel"],
        div[data-testid="stMetricLabel"] * {
            color: #667085 !important;
        }
        div[data-testid="stMetricValue"],
        div[data-testid="stMetricValue"] * {
            color: #101828 !important;
        }

        /* Inputs */
        [data-testid="stTextInput"] label,
        [data-testid="stTextArea"] label,
        [data-testid="stSelectbox"] label,
        [data-testid="stFileUploader"] label {
            color: #344054 !important;
        }
        [data-testid="stTextInput"] input,
        [data-testid="stTextArea"] textarea {
            color: #101828 !important;
            background: #FFFFFF !important;
        }

        /* Alerts */
        [data-testid="stAlert"] p,
        [data-testid="stAlert"] span {
            color: inherit !important;
        }

        .section-title {
            font-size: 1.15rem;
            font-weight: 700;
            color: #101828 !important;
            margin-top: 1rem;
        }
        .status-pill {
            padding: 5px 10px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
        }
        .success-box {
            background: #ECFDF3;
            border: 1px solid #ABEFC6;
            color: #067647 !important;
            padding: 12px;
            border-radius: 10px;
        }
        .info-box {
            background: #EFF8FF;
            border: 1px solid #B2DDFF;
            color: #175CD3 !important;
            padding: 12px;
            border-radius: 10px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# ------------------------- Session State ---------------------

if "access_token" not in st.session_state:
    st.session_state.access_token = None

if "auth_user" not in st.session_state:
    st.session_state.auth_user = None

if "user_id" not in st.session_state:
    st.session_state.user_id = None

if "last_upload_result" not in st.session_state:
    st.session_state.last_upload_result = None


def clear_authentication(message=None):
    """Clear the current login session without changing backend data."""
    st.session_state.access_token = None
    st.session_state.auth_user = None
    st.session_state.user_id = None
    st.session_state.auth_message = message


def show_login_page():
    """Render sign-in and account registration through FastAPI."""
    st.markdown(
        '<p class="main-title">FinWell AI</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="subtitle">Sign in or create an account to access your financial workspace.</p>',
        unsafe_allow_html=True,
    )

    left, center, right = st.columns([1, 1.25, 1])
    with center:
        if "auth_page_mode" not in st.session_state:
            st.session_state.auth_page_mode = "Sign in"

        mode = st.radio(
            "Account access",
            ["Sign in", "Create account"],
            horizontal=True,
            key="auth_page_mode",
            label_visibility="collapsed",
        )

        message = st.session_state.pop("auth_message", None)
        if message:
            st.success(message)

        if mode == "Create account":
            st.subheader("Create your FinWell account")
            with st.form("finwell_register_form"):
                username = st.text_input(
                    "Username",
                    placeholder="Choose a username (at least 3 characters)",
                    max_chars=100,
                )
                email = st.text_input(
                    "Email address",
                    placeholder="you@example.com",
                    max_chars=255,
                )
                password = st.text_input(
                    "Password",
                    type="password",
                    help="Use at least 12 characters.",
                )
                confirm_password = st.text_input(
                    "Confirm password",
                    type="password",
                )
                submitted = st.form_submit_button(
                    "Create account",
                    type="primary",
                    use_container_width=True,
                )

            if submitted:
                clean_username = username.strip()
                clean_email = email.strip().lower()

                if len(clean_username) < 3:
                    st.error("Username must contain at least 3 characters.")
                elif not clean_email or "@" not in clean_email:
                    st.error("Enter a valid email address.")
                elif len(password) < 12:
                    st.error("Password must contain at least 12 characters.")
                elif len(password) > 128:
                    st.error("Password must not exceed 128 characters.")
                elif password != confirm_password:
                    st.error("The passwords do not match.")
                else:
                    try:
                        response = requests.post(
                            f"{API_BASE_URL.rstrip('/')}/api/auth/register",
                            json={
                                "username": clean_username,
                                "email": clean_email,
                                "password": password,
                            },
                            timeout=15,
                        )

                        if response.status_code in (200, 201):
                            # Do not mutate the radio widget's own session-state key
                            # after it has been instantiated in this Streamlit run.
                            st.session_state.auth_message = (
                                "Account created successfully. Select 'Sign in' above and log in with your new credentials."
                            )
                            st.rerun()
                        elif response.status_code == 409:
                            st.error(
                                "An account with that username or email already exists. "
                                "Try signing in or use different details."
                            )
                        elif response.status_code == 422:
                            try:
                                detail = response.json().get("detail", "Please check the registration details.")
                            except ValueError:
                                detail = "Please check the registration details."
                            st.error(str(detail))
                        else:
                            try:
                                detail = response.json().get("detail", response.text)
                            except ValueError:
                                detail = response.text
                            st.error(f"Registration failed (HTTP {response.status_code}): {detail}")

                    except requests.exceptions.ConnectionError:
                        st.error("Cannot connect to FastAPI. Start the backend and try again.")
                    except requests.exceptions.Timeout:
                        st.error("The registration request timed out. Please try again.")
                    except Exception as exc:
                        st.error(f"Unable to create account: {exc}")

        else:
            st.subheader("Welcome back")
            with st.form("finwell_login_form"):
                email = st.text_input(
                    "Email address",
                    placeholder="you@example.com",
                )
                password = st.text_input(
                    "Password",
                    type="password",
                )
                submitted = st.form_submit_button(
                    "Sign in",
                    type="primary",
                    use_container_width=True,
                )

            if submitted:
                if not email.strip() or not password:
                    st.error("Enter both your email address and password.")
                else:
                    try:
                        response = requests.post(
                            f"{API_BASE_URL.rstrip('/')}/api/auth/login",
                            json={
                                "email": email.strip().lower(),
                                "password": password,
                            },
                            timeout=15,
                        )

                        if response.status_code == 200:
                            result = response.json()
                            token = result.get("access_token")
                            user = result.get("user") or {}

                            if not token:
                                st.error("The login response did not contain an access token.")
                            else:
                                st.session_state.access_token = token
                                st.session_state.auth_user = user
                                st.session_state.user_id = user.get("user_id")
                                st.session_state.pop("auth_message", None)
                                st.rerun()
                        elif response.status_code in (401, 422):
                            try:
                                detail = response.json().get("detail", "Invalid login details.")
                            except ValueError:
                                detail = "Invalid login details."
                            st.error(str(detail))
                        else:
                            st.error(
                                f"Login failed (HTTP {response.status_code}). "
                                "Check that the FastAPI backend is running."
                            )

                    except requests.exceptions.ConnectionError:
                        st.error("Cannot connect to FastAPI. Start the backend and try again.")
                    except requests.exceptions.Timeout:
                        st.error("The login request timed out. Please try again.")
                    except Exception as exc:
                        st.error(f"Unable to sign in: {exc}")

        st.caption(f"Backend: {API_BASE_URL}")


# Show only the login screen until a valid login has been established.
if not st.session_state.access_token:
    show_login_page()
    st.stop()

# Temporary JWT display for API testing
st.sidebar.text_input(
    "JWT token (temporary)",
    value=st.session_state.access_token or "",
    type="password"
)    


# ------------------------- API Helpers -----------------------


def auth_headers():
    """Return the JWT Bearer header for protected API requests."""
    token = st.session_state.get("access_token")
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def handle_unauthorized(response):
    """End the local session if the backend rejects/has expired the JWT."""
    if response.status_code == 401:
        clear_authentication("Your session has expired. Please sign in again.")
        st.rerun()

def api_get(endpoint, params=None, timeout=30):
    """GET request to the FastAPI backend."""
    url = f"{API_BASE_URL.rstrip('/')}/{endpoint.lstrip('/')}"

    try:
        response = requests.get(
            url,
            params=params,
            headers=auth_headers(),
            timeout=timeout,
        )
        handle_unauthorized(response)

        if response.status_code == 200:
            return response.json()

        return {
            "success": False,
            "status_code": response.status_code,
            "detail": response.text,
        }

    except requests.exceptions.ConnectionError:
        return {
            "success": False,
            "detail": "Cannot connect to FastAPI. Is the backend running?",
        }

    except requests.exceptions.Timeout:
        return {
            "success": False,
            "detail": "The API request timed out.",
        }

    except Exception as exc:
        return {
            "success": False,
            "detail": str(exc),
        }


def api_post_file(endpoint, uploaded_file, data=None, timeout=180):
    """Upload a file to FastAPI using multipart/form-data."""
    url = f"{API_BASE_URL.rstrip('/')}/{endpoint.lstrip('/')}"

    try:
        uploaded_file.seek(0)

        files = {
            "file": (
                uploaded_file.name,
                uploaded_file.getvalue(),
                uploaded_file.type or "application/pdf",
            )
        }

        response = requests.post(
            url,
            files=files,
            data=data or {},
            headers=auth_headers(),
            timeout=timeout,
        )
        handle_unauthorized(response)

        try:
            result = response.json()
        except ValueError:
            result = {"detail": response.text}

        if response.ok:
            return result

        return {
            "success": False,
            "status_code": response.status_code,
            "detail": result.get("detail", result),
        }

    except requests.exceptions.ConnectionError:
        return {
            "success": False,
            "detail": "Cannot connect to FastAPI. Is the backend running?",
        }

    except requests.exceptions.Timeout:
        return {
            "success": False,
            "detail": "Upload timed out. Check the backend terminal.",
        }

    except Exception as exc:
        return {
            "success": False,
            "detail": str(exc),
        }


def get_documents():
    """Fetch documents belonging to the authenticated user."""
    result = api_get("/api/documents")

    if isinstance(result, list):
        return result

    if isinstance(result, dict):
        # Support common response formats.
        for key in ["documents", "data", "results", "items"]:
            if isinstance(result.get(key), list):
                return result[key]

    return []


def get_document_text(document_id):
    """Fetch extracted text for a document."""
    result = api_get(f"/api/documents/{document_id}/text")

    if isinstance(result, str):
        return result

    if isinstance(result, dict):
        for key in ["text", "extracted_text", "full_text", "content"]:
            if isinstance(result.get(key), str):
                return result[key]

    return result


def get_document_detail(document_id):
    """Fetch document metadata."""
    return api_get(f"/api/documents/{document_id}")


def format_currency(value):
    try:
        return f"₹{float(value):,.2f}"
    except (TypeError, ValueError):
        return "—"


def first_available(data, keys, default=None):
    if not isinstance(data, dict):
        return default

    for key in keys:
        if data.get(key) is not None:
            return data[key]

    return default


def normalize_documents(documents):
    """Normalize document fields for display without changing backend data."""
    normalized = []

    for doc in documents:
        if not isinstance(doc, dict):
            continue

        normalized.append({
            "Document ID": first_available(
                doc,
                ["document_id", "id"],
                "—",
            ),
            "Filename": first_available(
                doc,
                ["filename", "file_name", "original_filename", "name"],
                "Unknown file",
            ),
            "Type": first_available(
                doc,
                ["document_type", "doc_type", "type"],
                "Unknown",
            ),
            "Status": first_available(
                doc,
                ["status", "processing_status"],
                "Unknown",
            ),
            "Uploaded": first_available(
                doc,
                ["created_at", "uploaded_at", "upload_date"],
                "—",
            ),
            "Transactions": first_available(
                doc,
                ["transaction_count", "stored_transaction_count"],
                0,
            ),
        })

    return normalized


# ------------------------- Sidebar ---------------------------

with st.sidebar:
    st.markdown("## 💠 FinWell AI")
    st.caption("Personal Finance Intelligence")

    st.divider()

    navigation_pages = [
        "Dashboard",
        "Upload Documents",
        "Documents",
        "Transactions",
        "Document Viewer",
        "AI Search",
    ]
    if "navigation_target" in st.session_state:
        target = st.session_state.pop("navigation_target")
        if target in navigation_pages:
            st.session_state["finwell_navigation"] = target
    if "finwell_navigation" not in st.session_state:
        st.session_state["finwell_navigation"] = "Dashboard"

    page = st.radio(
        "Navigation",
        navigation_pages,
        key="finwell_navigation",
        label_visibility="collapsed",
    )

    st.divider()

    current_user = st.session_state.get("auth_user") or {}
    display_name = (
        current_user.get("username")
        or current_user.get("email")
        or "Authenticated user"
    )
    st.caption(f"Signed in as: {display_name}")

    if st.button("Log out", use_container_width=True):
        clear_authentication("You have been signed out.")
        st.rerun()

    st.divider()
    st.caption("Backend")
    st.code(API_BASE_URL, language=None)

    if st.button("🔄 Refresh data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()


# ------------------------- Header ----------------------------

st.markdown(
    '<p class="main-title">FinWell AI</p>',
    unsafe_allow_html=True,
)
st.markdown(
    '<p class="subtitle">Understand your finances. Make smarter decisions.</p>',
    unsafe_allow_html=True,
)

# Backend health check
health = api_get("/health", timeout=5)

if isinstance(health, dict) and health.get("success") is False:
    # The API may return a normal health JSON without a success key.
    backend_online = False
else:
    backend_online = True

status_col1, status_col2 = st.columns([5, 1])

with status_col1:
    signed_in_user = st.session_state.get("auth_user") or {}
    st.caption(
        f"Signed in as: {signed_in_user.get('username') or signed_in_user.get('email') or 'Authenticated user'}"
    )

with status_col2:
    if backend_online:
        st.success("API connected", icon="🟢")
    else:
        st.warning("API status unknown", icon="🟠")


# Load documents for pages that need them.
documents = get_documents()
normalized_documents = normalize_documents(documents)
documents_df = pd.DataFrame(normalized_documents)


# ============================================================
# PAGE: DASHBOARD
# ============================================================

if page == "Dashboard":
    st.subheader("Financial Overview")

    total_documents = len(documents_df)

    completed_documents = 0
    processing_documents = 0
    failed_documents = 0

    if not documents_df.empty:
        status_series = documents_df["Status"].astype(str).str.lower()

        completed_documents = status_series.isin(
            ["completed", "complete", "success", "processed"]
        ).sum()

        processing_documents = status_series.isin(
            ["processing", "pending", "queued"]
        ).sum()

        failed_documents = status_series.isin(
            ["failed", "error"]
        ).sum()

    metric1, metric2, metric3, metric4 = st.columns(4)

    metric1.metric("Documents", total_documents)
    metric2.metric("Completed", int(completed_documents))
    metric3.metric("Processing", int(processing_documents))
    metric4.metric("Failed", int(failed_documents))

    st.markdown("### Recent Documents")

    if documents_df.empty:
        st.info(
            "No documents found yet. Upload a bank statement PDF to get started."
        )
    else:
        recent_df = documents_df.head(5)
        st.dataframe(
            recent_df,
            use_container_width=True,
            hide_index=True,
        )

    st.markdown("### Quick Actions")

    quick1, quick2, quick3 = st.columns(3)

    with quick1:
        if st.button("📄 Upload a statement", use_container_width=True):
            st.session_state["navigation_target"] = "Upload Documents"
            st.rerun()

    with quick2:
        if st.button("📚 View documents", use_container_width=True):
            st.session_state["navigation_target"] = "Documents"
            st.rerun()

    with quick3:
        if st.button("🔎 Search documents", use_container_width=True):
            st.session_state["navigation_target"] = "AI Search"
            st.rerun()

    st.caption(
        "Transaction totals and financial insights will be connected "
        "when the calculation and reconciliation APIs are available."
    )


# ============================================================
# PAGE: UPLOAD DOCUMENTS
# ============================================================

elif page == "Upload Documents":
    st.subheader("Upload Financial Documents")

    st.markdown(
        """
        Upload a digitally generated bank statement PDF.
        The backend validates the file, extracts text, classifies it,
        parses transactions, stores data in MySQL, and indexes text in ChromaDB.
        """
    )

    uploaded_file = st.file_uploader(
        "Choose a PDF statement",
        type=["pdf"],
        help="Maximum file size: 20 MB.",
    )

    if uploaded_file:
        file_size_mb = uploaded_file.size / (1024 * 1024)

        file_col1, file_col2, file_col3 = st.columns(3)

        file_col1.metric("Filename", uploaded_file.name)
        file_col2.metric("File size", f"{file_size_mb:.2f} MB")
        file_col3.metric("Format", "PDF")

        if file_size_mb > MAX_FILE_SIZE_MB:
            st.error(f"File exceeds the {MAX_FILE_SIZE_MB} MB limit.")

        else:
            if st.button(
                "🚀 Process document",
                type="primary",
                use_container_width=True,
            ):
                with st.spinner(
                    "Uploading and processing your document..."
                ):
                    result = api_post_file(
                        "/api/upload",
                        uploaded_file,
                        data={},
                    )

                st.session_state.last_upload_result = result

                if isinstance(result, dict) and result.get("success") is False:
                    st.error("Upload failed.")
                    st.json(result)

                elif isinstance(result, dict) and result.get("detail"):
                    st.error("The backend returned an error.")
                    st.json(result)

                else:
                    st.success("Document uploaded and processed.")
                    st.json(result)

                    st.info(
                        "Refresh the Documents page to see the new record."
                    )

    if st.session_state.last_upload_result:
        st.markdown("### Last Upload Result")
        st.json(st.session_state.last_upload_result)


# ============================================================
# PAGE: DOCUMENTS
# ============================================================

elif page == "Documents":
    st.subheader("Your Documents")

    if documents_df.empty:
        st.info("No documents are available for this user.")
    else:
        search_text = st.text_input(
            "Search by filename or document type",
            placeholder="e.g. Meridian, bank statement",
        )

        filtered_df = documents_df.copy()

        if search_text:
            mask = (
                filtered_df["Filename"].astype(str).str.contains(
                    search_text,
                    case=False,
                    na=False,
                )
                |
                filtered_df["Type"].astype(str).str.contains(
                    search_text,
                    case=False,
                    na=False,
                )
            )

            filtered_df = filtered_df[mask]

        st.dataframe(
            filtered_df,
            use_container_width=True,
            hide_index=True,
        )

        document_ids = [
            str(x)
            for x in filtered_df["Document ID"].tolist()
            if str(x) != "—"
        ]

        if document_ids:
            selected_id = st.selectbox(
                "Select a document to inspect",
                document_ids,
            )

            if st.button("View document details"):
                detail = get_document_detail(selected_id)
                st.json(detail)


# ============================================================
# PAGE: TRANSACTIONS
# ============================================================

elif page == "Transactions":
    st.subheader("Transactions")

    st.info(
        "The transaction storage module is working. "
        "This page will display live transaction rows once the "
        "transactions-list API route is exposed by FastAPI."
    )

    st.markdown("#### API route expected by this page")

    st.code(
        "GET /api/transactions",
        language="http",
    )

    st.markdown(
        """
        Suggested response format:

        ```json
        {
          "transactions": [
            {
              "transaction_id": 55,
              "document_id": 9,
              "transaction_date": "2026-10-01",
              "description": "Salary credit",
              "debit": null,
              "credit": 78000.00,
              "balance": 120350.75
            }
          ]
        }
        ```
        """
    )

    if st.button("Try loading transactions"):
        result = api_get("/api/transactions")

        if isinstance(result, dict):
            transaction_rows = result.get(
                "transactions",
                result.get("data", []),
            )
        elif isinstance(result, list):
            transaction_rows = result
        else:
            transaction_rows = []

        if transaction_rows:
            transactions_df = pd.DataFrame(transaction_rows)
            st.dataframe(
                transactions_df,
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.warning(
                "No transaction list was returned. "
                "The route may not exist yet."
            )
            st.json(result)


# ============================================================
# PAGE: DOCUMENT VIEWER
# ============================================================

elif page == "Document Viewer":
    st.subheader("Extracted Document Text")

    if documents_df.empty:
        st.info("Upload a document first.")
    else:
        document_ids = [
            str(x)
            for x in documents_df["Document ID"].tolist()
            if str(x) != "—"
        ]

        selected_id = st.selectbox(
            "Choose a document",
            document_ids,
        )

        if st.button("Load extracted text", type="primary"):
            with st.spinner("Loading extracted text..."):
                extracted_text = get_document_text(selected_id)

            if isinstance(extracted_text, str):
                st.text_area(
                    "Extracted text",
                    value=extracted_text,
                    height=500,
                )

                st.download_button(
                    "⬇️ Download extracted text",
                    data=extracted_text,
                    file_name=f"document_{selected_id}_text.txt",
                    mime="text/plain",
                )
            else:
                st.warning("Could not retrieve extracted text.")
                st.json(extracted_text)


# ============================================================
# PAGE: AI SEARCH
# ============================================================

elif page == "AI Search":
    st.subheader("Search Your Financial Documents")

    st.markdown(
        """
        Search across your uploaded financial documents.
        This page is prepared for the ChromaDB retrieval API.
        """
    )

    query = st.text_input(
        "Ask a question or enter a search phrase",
        placeholder="What was my home loan EMI?",
    )

    if st.button("🔎 Search documents", type="primary"):
        if not query.strip():
            st.warning("Enter a search query first.")
        else:
            with st.spinner("Searching your documents..."):
                result = api_get(
                    "/api/search",
                    params={"query": query},
                    timeout=60,
                )

            if isinstance(result, dict) and result.get("detail"):
                st.warning(
                    "The search API may not be connected yet."
                )
                st.json(result)

            else:
                st.markdown("### Search Results")
                st.json(result)

    st.caption(
        "This is document retrieval, not financial advice. "
        "The final AI assistant response will be integrated with your "
        "team's RAG module."
    )


# ------------------------- Footer ----------------------------

st.divider()

signed_in_user = st.session_state.get("auth_user") or {}
footer_identity = (
    signed_in_user.get("username")
    or signed_in_user.get("email")
    or "Authenticated user"
)
st.caption(
    f"FinWell AI • Financial Document Intelligence • {footer_identity}"
)