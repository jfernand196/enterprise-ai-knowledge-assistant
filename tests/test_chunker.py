import pytest

from app.domain.models import Document
from app.rag.chunker import split_into_chunks


def test_split_into_chunks_applies_size_and_overlap() -> None:
    document = Document(
        doc_id="demo",
        title="Demo",
        category="hr",
        content="A" * 120,
    )

    chunks = split_into_chunks(document, chunk_size=50, overlap=10)

    assert len(chunks) == 3
    assert chunks[0].text == "A" * 50
    assert chunks[0].chunk_id == "demo-0"


def test_split_into_chunks_rejects_invalid_overlap() -> None:
    document = Document(doc_id="demo", title="Demo", category="hr", content="hello")

    with pytest.raises(ValueError, match="overlap"):
        split_into_chunks(document, chunk_size=10, overlap=10)
