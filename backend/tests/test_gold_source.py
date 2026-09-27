import pytest

from app.knowledge.gold import load_gold_documents
from app.knowledge.index import build_knowledge_index
from app.lakehouse.databricks_client import DatabricksQueryError


class GoldSql:
    def execute(self, statement: str, parameters: list[dict[str, str]] | None = None) -> list[dict]:
        assert "knowledge_assistant`.`gold`.`documents" in statement
        return [
            {
                "id": "vacation_policy",
                "title": "Vacation Policy",
                "category": "hr",
                "content": "Employees receive 15 paid vacation days during their first year.",
            }
        ]


class EmptyGoldSql:
    def execute(self, statement: str, parameters: list[dict[str, str]] | None = None) -> list[dict]:
        return []


def test_load_gold_documents_maps_delta_rows() -> None:
    documents = load_gold_documents(GoldSql(), "knowledge_assistant")

    assert documents[0].doc_id == "vacation_policy"
    assert documents[0].category == "hr"
    assert "15 paid vacation days" in documents[0].content


def test_load_gold_documents_rejects_empty_table() -> None:
    with pytest.raises(DatabricksQueryError):
        load_gold_documents(EmptyGoldSql(), "knowledge_assistant")


def test_index_retrieves_from_supplied_documents(tmp_path) -> None:
    documents = load_gold_documents(GoldSql(), "knowledge_assistant")
    index = build_knowledge_index(
        documents_dir=tmp_path,
        chunk_size=500,
        overlap=100,
        top_k=3,
        documents=documents,
    )

    matches = index.retriever.retrieve("How many vacation days?")

    assert matches[0].chunk.title == "Vacation Policy"
    assert "15 paid vacation days" in index.generator.generate("vacation", matches)
