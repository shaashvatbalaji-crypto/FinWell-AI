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
        metadata={"description": "FinWell AI financial document chunks"},
    )


def add_document_chunks(
    document_id,
    user_id,
    chunks,
    collection_name="financial_documents",
):
    """Store document text chunks in ChromaDB."""

    if not chunks:
        return {
            "success": False,
            "message": "No chunks were provided.",
            "stored_count": 0,
        }

    collection = get_or_create_collection(collection_name)

    ids = [
        f"user_{user_id}_doc_{document_id}_chunk_{index}"
        for index in range(len(chunks))
    ]

    metadatas = [
        {
            "document_id": int(document_id),
            "user_id": int(user_id),
            "chunk_index": index,
        }
        for index in range(len(chunks))
    ]

    collection.upsert(
        ids=ids,
        documents=chunks,
        metadatas=metadatas,
    )

    return {
        "success": True,
        "message": "Document chunks stored successfully.",
        "stored_count": len(chunks),
    }


def search_document_chunks(
    query,
    user_id,
    n_results=3,
    collection_name="financial_documents",
):
    """Search for relevant chunks belonging to a specific user."""

    if not query or not query.strip():
        return {
            "success": False,
            "message": "Search query cannot be empty.",
            "results": [],
        }

    collection = get_or_create_collection(collection_name)

    if collection.count() == 0:
        return {
            "success": True,
            "message": "The collection is empty.",
            "results": [],
        }

    results = collection.query(
        query_texts=[query],
        n_results=min(n_results, collection.count()),
        where={"user_id": int(user_id)},
        include=["documents", "metadatas", "distances"],
    )

    matches = []

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