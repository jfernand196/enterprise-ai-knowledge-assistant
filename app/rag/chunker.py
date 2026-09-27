from app.domain.models import Chunk, Document


def split_into_chunks(
    document: Document,
    chunk_size: int,
    overlap: int,
) -> list[Chunk]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be >= 0 and smaller than chunk_size")

    text = document.content.strip()
    if not text:
        return []

    chunks: list[Chunk] = []
    start = 0
    index = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        end = _end_at_sentence(text, start, end)
        piece = text[start:end].strip()
        if piece:
            chunks.append(
                Chunk(
                    chunk_id=f"{document.doc_id}-{index}",
                    doc_id=document.doc_id,
                    title=document.title,
                    category=document.category,
                    text=piece,
                )
            )
            index += 1
        if end == len(text):
            break
        next_start = end - overlap
        start = next_start if next_start > start else end
    return chunks


def _end_at_sentence(text: str, start: int, end: int) -> int:
    if end >= len(text):
        return len(text)
    window = text[start:end]
    boundary = max(window.rfind(". "), window.rfind(".\n"))
    if boundary < (end - start) // 2:
        return end
    return start + boundary + 1
