from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import PROJECT_ROOT
from app.lakehouse.delta import DeltaTable
from app.lakehouse.frame import Frame, sql_count_by_category
from app.lakehouse.pipeline import LakehousePipeline


def test_frame_filter_select_join_and_sql_group_by() -> None:
    documents = Frame(
        [
            {"id": "1", "category": "hr", "title": "Vacation"},
            {"id": "2", "category": "hr", "title": "Benefits"},
            {"id": "3", "category": "security", "title": "MFA"},
        ]
    )
    owners = Frame(
        [
            {"category": "hr", "owner_team": "People"},
            {"category": "security", "owner_team": "Security"},
        ]
    )

    joined = documents.filter(lambda row: row["category"] == "hr").join(owners, on="category")
    counts = sql_count_by_category(documents)

    assert [row["owner_team"] for row in joined.rows] == ["People", "People"]
    assert counts.rows == [
        {"category": "hr", "count": 2},
        {"category": "security", "count": 1},
    ]


def test_delta_merge_and_time_travel(tmp_path: Path) -> None:
    table = DeltaTable(tmp_path, "documents")
    table.write([{"id": "vacation_policy", "title": "Vacation Policy v1"}])
    table.merge([{"id": "vacation_policy", "title": "Vacation Policy v2"}], key="id")

    assert table.read(version=0)[0]["title"] == "Vacation Policy v1"
    assert table.read()[0]["title"] == "Vacation Policy v2"
    assert table.versions() == [0, 1]


def test_pipeline_builds_bronze_silver_gold(tmp_path: Path) -> None:
    pipeline = LakehousePipeline(tmp_path)
    result = pipeline.run(PROJECT_ROOT / "data" / "documents")

    assert result["bronze_rows"] == 4
    assert result["gold_documents"] == 4
    categories = {row["category"]: row["count"] for row in result["category_counts"]}
    assert categories["hr"] == 1
    gold = pipeline.gold_documents.read()
    assert {row["owner_team"] for row in gold} == {"People", "Security", "Product", "Support"}


def test_create_lakehouse_run_and_read_gold(client: TestClient) -> None:
    created = client.post("/lakehouse/runs")

    assert created.status_code == 200
    body = created.json()
    assert body["gold_documents"] == 4

    gold = client.get("/lakehouse/tables/gold/documents")
    assert gold.status_code == 200
    assert gold.json()["version"] == body["versions"]["gold.documents"]
    assert len(gold.json()["rows"]) == 4

    bronze_v0 = client.get("/lakehouse/tables/bronze/documents", params={"version": 0})
    assert bronze_v0.status_code == 200
    assert bronze_v0.json()["version"] == 0


def test_get_unknown_lakehouse_table_returns_404(client: TestClient) -> None:
    response = client.get("/lakehouse/tables/platinum/documents")

    assert response.status_code == 404
