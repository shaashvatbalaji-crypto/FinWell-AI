from chroma_pipeline.vector_store import (
    get_or_create_collection,
    add_document_chunks,
    search_document_chunks,
)


TEST_COLLECTION = "finwell_chunk_test"


# Clear only this dedicated test collection to make the test repeatable.
collection = get_or_create_collection(TEST_COLLECTION)

existing_ids = collection.get()["ids"]

if existing_ids:
    collection.delete(ids=existing_ids)


# Store sample chunks.
sample_chunks = [
    "The customer has a savings account with a monthly salary credit.",
    "The customer paid a monthly home loan EMI of 25000 rupees.",
    "The customer owns an investment in an equity mutual fund.",
]

store_result = add_document_chunks(
    document_id=999,
    user_id=1,
    chunks=sample_chunks,
    collection_name=TEST_COLLECTION,
)

print("Storage result:", store_result)


# Search for a relevant chunk.
search_result = search_document_chunks(
    query="How much is the monthly home loan payment?",
    user_id=1,
    n_results=2,
    collection_name=TEST_COLLECTION,
)

print("\nSearch result:")
for item in search_result["results"]:
    print("-", item["text"])
    print("  Distance:", item["distance"])


if (
    store_result["success"]
    and store_result["stored_count"] == 3
    and search_result["success"]
    and search_result["results"]
):
    print("\nPASS: Chunks stored and retrieved successfully.")
else:
    print("\nFAIL: ChromaDB chunk storage or retrieval failed.")