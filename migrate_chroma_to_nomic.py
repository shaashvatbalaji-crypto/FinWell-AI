import json
import urllib.request
import urllib.error

from chroma_pipeline.vector_store import (
    get_chroma_client,
    get_or_create_collection,
)

SOURCE_COLLECTION = "financial_documents"
TARGET_COLLECTION = "financial_documents_nomic_v1"

OLLAMA_URL = "http://localhost:11434/api/embeddings"
EMBEDDING_MODEL = "nomic-embed-text:latest"

EXPECTED_DIMENSION = 768
BATCH_SIZE = 5


def generate_embedding(text):
    payload = {
        "model": EMBEDDING_MODEL,
        "prompt": text
    }

    request = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as error:
        raise RuntimeError(f"Ollama connection failed: {error}")

    embedding = result.get("embedding")

    if not embedding or len(embedding) != EXPECTED_DIMENSION:
        raise RuntimeError(
            f"Invalid embedding dimensions: "
            f"{len(embedding) if embedding else 0}"
        )

    return embedding


def migrate():
    print("\n========== FINWELL CHROMA MIGRATION ==========")

    client = get_chroma_client()
    source = client.get_collection(SOURCE_COLLECTION)

    source_count = source.count()

    if source_count == 0:
        raise RuntimeError("Source collection is empty.")

    target = get_or_create_collection(TARGET_COLLECTION)

    print("Source:", SOURCE_COLLECTION)
    print("Target:", TARGET_COLLECTION)
    print("Source records:", source_count)
    print("Existing target records:", target.count())

    original = source.get(
        limit=source_count,
        include=["documents", "metadatas"]
    )

    ids = original["ids"]
    documents = original["documents"]
    metadatas = original["metadatas"]

    if not (len(ids) == len(documents) == len(metadatas)):
        raise RuntimeError("Source record counts do not match.")

    if any(doc is None or not doc.strip() for doc in documents):
        raise RuntimeError("Empty document found in source.")

    print("\nGenerating local Nomic embeddings...")

    for start in range(0, source_count, BATCH_SIZE):
        end = min(start + BATCH_SIZE, source_count)

        batch_ids = ids[start:end]
        batch_docs = documents[start:end]
        batch_metadata = metadatas[start:end]

        embeddings = []

        for index, document in enumerate(batch_docs):
            embeddings.append(generate_embedding(document))
            print(f"Embedded {start + index + 1}/{source_count}")

        target.upsert(
            ids=batch_ids,
            documents=batch_docs,
            metadatas=batch_metadata,
            embeddings=embeddings
        )

        print(f"Stored {end}/{source_count}")

    print("\n========== VALIDATION ==========")

    migrated = target.get(
        limit=target.count(),
        include=["documents", "metadatas", "embeddings"]
    )

    source_map = {
        ids[i]: (documents[i], metadatas[i])
        for i in range(source_count)
    }

    target_map = {
        migrated["ids"][i]: (
            migrated["documents"][i],
            migrated["metadatas"][i]
        )
        for i in range(len(migrated["ids"]))
    }

    missing = set(source_map) - set(target_map)
    extra = set(target_map) - set(source_map)

    mismatches = [
        record_id for record_id in source_map
        if record_id in target_map
        and source_map[record_id] != target_map[record_id]
    ]

    dimensions = {
        len(vector) for vector in migrated["embeddings"]
    }

    print("Original records:", source_count)
    print("Migrated records:", target.count())
    print("Missing IDs:", len(missing))
    print("Unexpected IDs:", len(extra))
    print("Content/metadata mismatches:", len(mismatches))
    print("Embedding dimensions:", dimensions)

    success = (
        target.count() == source_count
        and not missing
        and not extra
        and not mismatches
        and dimensions == {EXPECTED_DIMENSION}
    )

    if success:
        print("\nMIGRATION SUCCESSFUL")
        print("Original collection remains untouched.")
    else:
        print("\nMIGRATION VALIDATION FAILED")
        print("Do not switch application collections.")

    print("================================")


if __name__ == "__main__":
    migrate()
