
from pathlib import Path
import chromadb


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CHROMA_PATH = PROJECT_ROOT / "data" / "chroma_db"

CHROMA_PATH.mkdir(parents=True, exist_ok=True)


def get_chroma_client():
    """Return a persistent ChromaDB client."""
    return chromadb.PersistentClient(path=str(CHROMA_PATH))


def get_or_create_collection(collection_name="financial_documents"):
    """Get an existing collection or create it."""
    client = get_chroma_client()

    return client.get_or_create_collection(
        name=collection_name,
        metadata={
            "description": "FinWell AI financial document chunks"
        },
    )


def add_document_chunks(
    document_id,
    user_id,
    chunks,
    account_id=None,
    collection_name="financial_documents",
):
    """
    Store document text chunks in ChromaDB.

    Each chunk stores:
        user_id
        document_id
        chunk_index
        account_id (when available)

    Existing callers without account_id remain supported.
    """

    if not chunks:
        return {
            "success": False,
            "message": "No chunks were provided.",
            "stored_count": 0,
        }

    if not isinstance(user_id, int) or user_id <= 0:
        return {
            "success": False,
            "message": "Invalid user_id.",
            "stored_count": 0,
        }

    if not isinstance(document_id, int) or document_id <= 0:
        return {
            "success": False,
            "message": "Invalid document_id.",
            "stored_count": 0,
        }

    if account_id is not None:
        if (
            not isinstance(account_id, int)
            or isinstance(account_id, bool)
            or account_id <= 0
        ):
            return {
                "success": False,
                "message": "Invalid account_id.",
                "stored_count": 0,
            }

    try:
        collection = get_or_create_collection(collection_name)

        ids = [
            f"user_{user_id}_doc_{document_id}_chunk_{index}"
            for index in range(len(chunks))
        ]

        metadatas = []

        for index in range(len(chunks)):

            metadata = {
                "document_id": document_id,
                "user_id": user_id,
                "chunk_index": index,
            }

            # Do not store None in ChromaDB metadata.
            if account_id is not None:
                metadata["account_id"] = account_id

            metadatas.append(metadata)

        collection.upsert(
            ids=ids,
            documents=chunks,
            metadatas=metadatas,
        )

        return {
            "success": True,
            "message": "Document chunks stored successfully.",
            "stored_count": len(chunks),
            "document_id": document_id,
            "user_id": user_id,
            "account_id": account_id,
        }

    except Exception as error:
        return {
            "success": False,
            "message": f"ChromaDB storage failed: {error}",
            "stored_count": 0,
        }


def search_document_chunks(
    query,
    user_id,
    n_results=3,
    account_id=None,
    document_id=None,
    collection_name="financial_documents",
):
    """
    Search relevant chunks with optional account and document filters.

    Default behavior:
        Search all documents belonging to the user.

    With account_id:
        Search only documents associated with that account.

    With document_id:
        Search only chunks belonging to that document.
    """

    if not query or not query.strip():
        return {
            "success": False,
            "message": "Search query cannot be empty.",
            "results": [],
        }

    if not isinstance(user_id, int) or user_id <= 0:
        return {
            "success": False,
            "message": "Invalid user_id.",
            "results": [],
        }

    if account_id is not None:
        if (
            not isinstance(account_id, int)
            or isinstance(account_id, bool)
            or account_id <= 0
        ):
            return {
                "success": False,
                "message": "Invalid account_id.",
                "results": [],
            }

    if document_id is not None:
        if (
            not isinstance(document_id, int)
            or isinstance(document_id, bool)
            or document_id <= 0
        ):
            return {
                "success": False,
                "message": "Invalid document_id.",
                "results": [],
            }

    if not isinstance(n_results, int) or n_results <= 0:
        return {
            "success": False,
            "message": "n_results must be a positive integer.",
            "results": [],
        }

    try:
        collection = get_or_create_collection(collection_name)

        if collection.count() == 0:
            return {
                "success": True,
                "message": "The collection is empty.",
                "results": [],
            }

        # Always restrict retrieval to the requested user.
        filters = [
            {"user_id": user_id}
        ]

        if account_id is not None:
            filters.append({"account_id": account_id})

        if document_id is not None:
            filters.append({"document_id": document_id})

        if len(filters) == 1:
            where_filter = filters[0]
        else:
            where_filter = {
                "$and": filters
            }

        results = collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where_filter,
            include=[
                "documents",
                "metadatas",
                "distances",
            ],
        )

        matches = []

        if results["ids"]:
            for index in range(len(results["ids"][0])):

                matches.append({
                    "chunk_id": results["ids"][0][index],
                    "text": results["documents"][0][index],
                    "metadata": results["metadatas"][0][index],
                    "distance": results["distances"][0][index],
                })

        return {
            "success": True,
            "message": "Search completed successfully.",
            "results": matches,
        }

    except Exception as error:
        return {
            "success": False,
            "message": f"ChromaDB search failed: {error}",
            "results": [],
        }
