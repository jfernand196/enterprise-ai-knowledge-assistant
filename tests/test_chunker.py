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


def test_split_into_chunks_keeps_a_number_with_its_sentence() -> None:
    document = Document(
        doc_id="vacation_policy",
        title="Vacation Policy",
        category="hr",
        content=(
            "Employees receive 15 paid vacation days during their first year of employment. "
            "After two years of continuous service, the annual allowance increases to 20 paid vacation days. "
            "Unused vacation days do not roll over except when a manager freeze prevented the employee "
            "from taking time off. In that case, up to 5 days may be carried over."
        ),
    )

    chunks = split_into_chunks(document, chunk_size=180, overlap=20)
    carrier = next(chunk for chunk in chunks if "5 days" in chunk.text)

    assert "carried over." in carrier.text
    assert not carrier.text.endswith("5")


def test_split_into_chunks_rejects_invalid_overlap() -> None:
    document = Document(doc_id="demo", title="Demo", category="hr", content="hello")

    with pytest.raises(ValueError, match="overlap"):
        split_into_chunks(document, chunk_size=10, overlap=10)
