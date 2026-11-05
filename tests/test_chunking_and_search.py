from chroma_pipeline.chunker import chunk_text
from chroma_pipeline.vector_store import (
    get_or_create_collection,
    add_document_chunks,
    search_document_chunks,
)


TEST_COLLECTION = "finwell_pipeline_test"


# 1. Use distinct sample financial text.
sample_text = """
BANK STATEMENT

The customer receives a monthly salary credit of 75000 rupees.

The customer pays a home loan EMI of 25000 rupees every month.

The customer spends money on groceries and transportation.

The customer has an investment in an equity mutual fund.
"""


# 2. Split text into chunks.
chunks = chunk_text(
    sample_text,
    chunk_size=250,
    chunk_overlap=40,
)

print("Number of chunks created:", len(chunks))

for index, chunk in enumerate(chunks):
    print(f"\nChunk {index}:")
    print(chunk)


if not chunks:
    raise RuntimeError("Chunking failed: no chunks were created.")


# 3. Clear the dedicated test collection.
collection = get_or_create_collection(TEST_COLLECTION)

existing_ids = collection.get()["ids"]

if existing_ids:
    collection.delete(ids=existing_ids)


# 4. Store chunks in ChromaDB.
store_result = add_document_chunks(
    document_id=998,
    user_id=1,
    chunks=chunks,
    collection_name=TEST_COLLECTION,
)

print("\nStorage result:", store_result)

if not store_result["success"]:
    raise RuntimeError("ChromaDB storage failed.")


# 5. Confirm that the EMI detail exists in stored chunks.
stored_data = collection.get(
    where={"user_id": 1},
    include=["documents"],
)

emi_exists_in_storage = any(
    "25000" in text and "EMI" in text
    for text in stored_data["documents"]
)

print("\nEMI detail exists in stored chunks:", emi_exists_in_storage)


# 6. Search using a specific query and request more results.
search_result = search_document_chunks(
    query="home loan EMI payment 25000 rupees per month",
    user_id=1,
    n_results=10,
    collection_name=TEST_COLLECTION,
)

print("\nSearch results:")

for result in search_result["results"]:
    print("-", result["text"])
    print("  Distance:", result["distance"])


# 7. Confirm that relevant text was stored and retrieved.
relevant_result_found = any(
    "25000" in result["text"] and "EMI" in result["text"]
    for result in search_result["results"]
)

if (
    store_result["success"]
    and emi_exists_in_storage
    and search_result["success"]
    and relevant_result_found
):
    print("\nPASS: Text was chunked, stored, and relevant text retrieved.")
else:
    print("\nFAIL: Relevant financial text was not retrieved.")