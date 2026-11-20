from chroma_pipeline.vector_store import get_chroma_client
from chroma_pipeline.embedder import embed_text

COLLECTION_NAME = "financial_documents_nomic_v1"


def retrieve_chunks(
    query: str,
    user_id: int,
    top_k: int = 5
) -> list[dict]:

    if not query or not query.strip():
        raise ValueError("Query cannot be empty.")

    if not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("A valid user_id is required.")

    if top_k <= 0:
        raise ValueError("top_k must be greater than zero.")

    client = get_chroma_client()
    collection = client.get_collection(COLLECTION_NAME)

    if collection.count() == 0:
        return []

    query_embedding = embed_text(query)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, collection.count()),
        where={"user_id": user_id},
        include=["documents", "metadatas", "distances"]
    )

    retrieved = []

    for i, chunk_id in enumerate(results["ids"][0]):
        retrieved.append({
            "id": chunk_id,
            "text": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "distance": results["distances"][0][i]
        })

    return retrieved
