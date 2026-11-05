def chunk_text(
    text,
    chunk_size=1000,
    chunk_overlap=150,
):
    """
    Split text into chunks with overlap.

    Args:
        text: Extracted and cleaned document text.
        chunk_size: Maximum target characters per chunk.
        chunk_overlap: Characters repeated between adjacent chunks.

    Returns:
        A list of text chunks.
    """

    if not isinstance(text, str):
        raise TypeError("text must be a string")

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0")

    if chunk_overlap < 0:
        raise ValueError("chunk_overlap cannot be negative")

    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")

    text = text.strip()

    if not text:
        return []

    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = min(start + chunk_size, text_length)

        # Prefer ending at a paragraph or sentence boundary.
        if end < text_length:
            boundary = text.rfind("\n\n", start, end)

            if boundary == -1:
                boundary = text.rfind(". ", start, end)

            if boundary > start:
                end = boundary + 1

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= text_length:
            break

        next_start = end - chunk_overlap

        # Prevent an infinite loop if a boundary was too early.
        if next_start <= start:
            next_start = start + chunk_size - chunk_overlap

        start = next_start

    return chunks