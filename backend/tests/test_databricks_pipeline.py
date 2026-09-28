
import pytest
from fastapi.testclient import TestClient

from app.core.config import PROJECT_ROOT
from app.lakehouse.databricks_client import DatabricksQueryError, _rows
from app.lakehouse.databricks_pipeline import DatabricksLakehousePipeline
from app.lakehouse.identifiers import quote_identifier


class RecordingSql:
    def __init__(self) -> None:
        self.statements: list[str] = []

    def execute(self, statement: str, parameters: list[dict[str, str]] | None = None) -> list[dict]:
        self.statements.append(" ".join(statement.split()))
        if self.statements[-1].startswith("SELECT COUNT"):
            return [{"n": 4}]
        if self.statements[-1].startswith("SELECT category"):
            return [{"category": "hr", "count": 1}]
        if self.statements[-1].startswith("DESCRIBE HISTORY"):
            return [{"version": 2}]
        if self.statements[-1].startswith("SELECT *"):
            return [{"id": "vacation_policy"}]
        return []


def test_databricks_pipeline_writes_medallion_sql() -> None:
    client = RecordingSql()
    pipeline = DatabricksLakehousePipeline(client, "knowledge_assistant")

    result = pipeline.run(PROJECT_ROOT / "data" / "documents")

    sql = "\n".join(client.statements)
    assert "CREATE TABLE IF NOT EXISTS `knowledge_assistant`.`bronze`.`documents`" in sql
    assert "INSERT OVERWRITE `knowledge_assistant`.`bronze`.`documents`" in sql
    assert "MERGE INTO `knowledge_assistant`.`silver`.`documents`" in sql
    assert "INSERT OVERWRITE `knowledge_assistant`.`gold`.`documents`" in sql
    assert "INSERT OVERWRITE `knowledge_assistant`.`gold`.`category_counts`" in sql
    assert result["bronze_rows"] == 4
    assert result["gold_documents"] == 4
    assert result["versions"]["bronze.documents"] == 2


def test_databricks_pipeline_rejects_unknown_table() -> None:
    pipeline = DatabricksLakehousePipeline(RecordingSql(), "knowledge_assistant")

    with pytest.raises(KeyError):
        pipeline.read("platinum", "documents")


def test_databricks_pipeline_rejects_missing_version() -> None:
    pipeline = DatabricksLakehousePipeline(RecordingSql(), "knowledge_assistant")

    with pytest.raises(FileNotFoundError):
        pipeline.read("bronze", "documents", version=9)


def test_quote_identifier_rejects_sql() -> None:
    with pytest.raises(ValueError):
        quote_identifier("bronze;drop")


def test_statement_rows_coerce_numeric_columns() -> None:
    rows = _rows(
        {
            "manifest": {
                "schema": {
                    "columns": [
                        {"name": "category", "type_name": "STRING"},
                        {"name": "count", "type_name": "LONG"},
                    ]
                }
            },
            "result": {"data_array": [["hr", "2"]]},
        }
    )

    assert rows == [{"category": "hr", "count": 2}]


def test_databricks_query_error_returns_502(client: TestClient) -> None:
    class FailingLakehouse:
        def create_run(self) -> None:
            raise DatabricksQueryError("warehouse unavailable")

    client.app.state.lakehouse_service = FailingLakehouse()
    response = client.post("/lakehouse/runs")

    assert response.status_code == 502
    assert response.json()["detail"] == "warehouse unavailable"
