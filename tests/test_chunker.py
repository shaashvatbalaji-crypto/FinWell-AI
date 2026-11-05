from chroma_pipeline.chunker import chunk_text


# Test 1: Empty text
assert chunk_text("") == []
print("PASS: Empty text returns no chunks.")


# Test 2: Short text
short_text = "This is a short financial document."
short_chunks = chunk_text(short_text, chunk_size=100, chunk_overlap=10)

assert len(short_chunks) == 1
assert short_chunks[0] == short_text
print("PASS: Short text remains one chunk.")


# Test 3: Long text creates multiple chunks
long_text = (
    "The customer deposited salary into the savings account. "
    "The customer paid a home loan EMI. "
    "The customer invested in a mutual fund. "
) * 30

chunks = chunk_text(
    long_text,
    chunk_size=300,
    chunk_overlap=50,
)

assert len(chunks) > 1
assert all(chunk.strip() for chunk in chunks)
print(f"PASS: Long text split into {len(chunks)} non-empty chunks.")


# Test 4: Invalid overlap is rejected
try:
    chunk_text("Sample text", chunk_size=100, chunk_overlap=100)
    raise AssertionError("Expected ValueError was not raised.")
except ValueError:
    print("PASS: Invalid overlap is rejected.")


print("\nAll chunker tests passed!")