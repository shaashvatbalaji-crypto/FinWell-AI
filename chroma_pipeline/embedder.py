import json
import urllib.request
import urllib.error

OLLAMA_URL = "http://localhost:11434/api/embeddings"
MODEL = "nomic-embed-text:latest"
EXPECTED_DIMENSION = 768


def embed_text(text: str) -> list[float]:
    if not text or not text.strip():
        raise ValueError("Cannot embed empty text.")

    payload = {
        "model": MODEL,
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
        raise RuntimeError(f"Ollama embedding error: {error}")

    embedding = result.get("embedding")

    if not embedding or len(embedding) != EXPECTED_DIMENSION:
        raise RuntimeError(
            f"Expected 768 dimensions; received "
            f"{len(embedding) if embedding else 0}"
        )

    return embedding
