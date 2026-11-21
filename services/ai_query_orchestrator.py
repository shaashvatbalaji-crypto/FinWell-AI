"""
FinWell AI query orchestrator.

Routes user questions to the existing MySQL structured retrieval layer and
ChromaDB RAG pipeline. Qwen only explains retrieved evidence; it does not
execute SQL or mutate financial/reconciliation records.
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from mysql_pipeline.structured_retrieval_service import (
    get_structured_financial_data,
)
from mysql_pipeline.reconciliation_case_storage import get_case_by_id

# Existing RAG functions in the project.
from chroma_pipeline.retriever import retrieve_chunks
from chroma_pipeline.generator import generate_answer


CASE_ID_PATTERN = re.compile(
    r"\b(?:case|reconciliation\s+case)\s*(?:#|id\s*)?(\d+)\b",
    re.IGNORECASE,
)

DOCUMENT_TERMS = {
    "statement", "document", "pdf", "uploaded", "bank statement",
    "loan agreement", "interest rate", "emi", "invoice", "receipt",
    "what does", "according to", "in the document", "from my",
}
RECONCILIATION_TERMS = {
    "reconciliation", "reconcile", "matched", "match", "matches",
    "unmatched", "pending match", "duplicate", "internal transfer",
    "refund", "settlement", "allocation", "case", "discrepancy",
}
TRANSACTION_TERMS = {
    "transaction", "spent", "spend", "expense", "income", "credit",
    "debit", "payment", "received", "cash flow", "monthly",
    "balance", "account", "loan", "investment", "portfolio",
    "financial summary", "financial overview", "how much", "total",
}


def _json_default(value: Any):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return str(value)


def _safe_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, default=_json_default)


def _detect_sources(question: str) -> set[str]:
    """Deterministic routing only; no model-generated SQL or tool selection."""
    q = question.lower()
    sources: set[str] = set()

    if any(term in q for term in RECONCILIATION_TERMS):
        sources.add("reconciliation")

    if any(term in q for term in TRANSACTION_TERMS):
        sources.update({"analytics", "transactions"})

    if any(term in q for term in DOCUMENT_TERMS):
        sources.add("documents")

    # A financial question may refer to evidence in a statement as well as
    # structured records. Retrieve both when wording suggests document context.
    if not sources:
        sources.update({"analytics", "transactions", "documents"})

    # Case-specific requests need case details, not just the case list.
    if CASE_ID_PATTERN.search(question):
        sources.add("reconciliation")

    return sources


def _build_structured_context(
    user_id: int,
    sources: set[str],
    question: str,
) -> dict:
    include = set()
    if "analytics" in sources:
        include.add("analytics")
    if "transactions" in sources:
        include.add("transactions")
    if "reconciliation" in sources:
        include.add("reconciliation")

    # Account/loan/investment questions are covered by the unified service.
    q = question.lower()
    if any(word in q for word in ("account", "loan", "emi", "investment", "portfolio")):
        include.update({"accounts", "loans", "investments"})

    if not include:
        return {"success": True, "sections_requested": [], "section_status": {}, "data": {}}

    result = get_structured_financial_data(
        user_id=user_id,
        include=sorted(include),
        transaction_limit=100,
        reconciliation_limit=100,
        case_limit=50,
    )

    case_match = CASE_ID_PATTERN.search(question)
    if case_match:
        case_id = int(case_match.group(1))
        # Ownership is enforced inside get_case_by_id(user_id, case_id).
        result.setdefault("data", {})["requested_case_detail"] = get_case_by_id(
            user_id=user_id,
            case_id=case_id,
        )

    return result


def _as_context_chunks(structured_data: dict, document_chunks: list[dict]) -> list[dict]:
    """
    Adapt structured MySQL results to the existing generator's retrieved_chunks
    interface. This preserves the current generator and avoids duplicate LLM code.
    """
    chunks: list[dict] = []

    if structured_data and structured_data.get("data"):
        chunks.append({
            "id": "mysql_structured_financial_data",
            "text": (
                "AUTHORITATIVE STRUCTURED DATA FROM MYSQL. "
                "Use these records for exact financial figures and statuses. "
                "Do not infer missing values.\n"
                + _safe_json(structured_data)
            ),
            "metadata": {"source": "mysql", "authority": "structured"},
        })

    for index, chunk in enumerate(document_chunks or []):
        text = chunk.get("text") or chunk.get("document") or ""
        if not text:
            continue
        chunks.append({
            "id": chunk.get("id") or chunk.get("chunk_id") or f"document_chunk_{index}",
            "text": (
                "DOCUMENT EVIDENCE (may be incomplete; do not treat as a complete "
                "transaction ledger):\n" + str(text)
            ),
            "metadata": chunk.get("metadata") or {},
        })

    return chunks


def answer_financial_question(user_id: int, question: str) -> dict:
    """Return an evidence-grounded answer for one authenticated user."""
    if isinstance(user_id, bool) or not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("user_id must be a positive integer.")

    if not isinstance(question, str) or not question.strip():
        raise ValueError("question cannot be empty.")

    question = question.strip()
    if len(question) > 2000:
        raise ValueError("question must be 2000 characters or fewer.")

    sources = _detect_sources(question)

    structured_result = {"success": True, "sections_requested": [], "section_status": {}, "data": {}}
    if sources.intersection({"analytics", "transactions", "reconciliation"}):
        structured_result = _build_structured_context(user_id, sources, question)

    document_chunks = []
    document_retrieval_status = "not_requested"
    if "documents" in sources:
        try:
            # retrieve_chunks enforces the user_id filter in ChromaDB.
            document_chunks = retrieve_chunks(
                query=question,
                user_id=user_id,
                top_k=5,
            )
            document_retrieval_status = "success"
        except Exception as error:
            document_retrieval_status = f"failed: {error}"

    context_chunks = _as_context_chunks(structured_result, document_chunks)
    if not context_chunks:
        return {
            "success": False,
            "answer": (
                "I couldn't retrieve relevant financial records or document "
                "evidence for that question. Please check that your documents "
                "have been processed and try again."
            ),
            "sources": [],
            "retrieval_status": {
                "structured": structured_result.get("section_status", {}),
                "documents": document_retrieval_status,
            },
        }

    # Existing Qwen generator remains responsible only for grounded explanation.
    answer = generate_answer(question, context_chunks)

    source_labels = []
    if structured_result.get("data"):
        source_labels.append("mysql")
    if document_chunks:
        source_labels.append("chroma")

    return {
        "success": True,
        "answer": answer,
        "sources": source_labels,
        "retrieval_status": {
            "structured": structured_result.get("section_status", {}),
            "documents": document_retrieval_status,
        },
    }
