from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.knowledge.loader import load_documents
from app.lakehouse.databricks_client import DatabricksQueryError, SqlClient
from app.lakehouse.identifiers import qualify
from app.lakehouse.pipeline import OWNERS

TABLES = {
    ("bronze", "documents"): ("bronze", "documents"),
    ("silver", "documents"): ("silver", "documents"),
    ("gold", "documents"): ("gold", "documents"),
    ("gold", "category_counts"): ("gold", "category_counts"),
}


class DatabricksLakehousePipeline:
    def __init__(self, client: SqlClient, catalog: str) -> None:
        self._client = client
        self._catalog = catalog

    def run(self, documents_dir: Path) -> dict[str, int | list | dict]:
        ingested_at = datetime.now(UTC).isoformat()
        bronze_rows = [
            {
                "id": document.doc_id,
                "title": document.title,
                "category": document.category,
                "content": document.content,
                "ingested_at": ingested_at,
            }
            for document in load_documents(documents_dir)
        ]
        self._ensure_tables()
        self._overwrite_bronze(bronze_rows)
        self._client.execute(_merge_silver(self._table("silver", "documents"), self._table("bronze", "documents")))
        owners_sql, owners_params = _owners_source()
        self._client.execute(
            _overwrite_gold_documents(self._table("gold", "documents"), self._table("silver", "documents"), owners_sql),
            owners_params,
        )
        self._client.execute(
            _overwrite_category_counts(self._table("gold", "category_counts"), self._table("silver", "documents"))
        )
        return {
            "bronze_rows": self._count(self._table("bronze", "documents")),
            "silver_rows": self._count(self._table("silver", "documents")),
            "gold_documents": self._count(self._table("gold", "documents")),
            "category_counts": self._client.execute(
                f"SELECT category, `count` FROM {self._table('gold', 'category_counts')}"
            ),
            "versions": {
                "bronze.documents": self._latest_version(self._table("bronze", "documents")),
                "silver.documents": self._latest_version(self._table("silver", "documents")),
                "gold.documents": self._latest_version(self._table("gold", "documents")),
                "gold.category_counts": self._latest_version(self._table("gold", "category_counts")),
            },
        }

    def read(self, layer: str, name: str, version: int | None = None) -> tuple[int | None, list[dict[str, Any]]]:
        schema_table = TABLES.get((layer, name))
        if schema_table is None:
            raise KeyError(f"Unknown table: {layer}.{name}")
        table = qualify(self._catalog, schema_table[0], schema_table[1])
        latest = self._latest_version(table)
        if version is None:
            rows = self._client.execute(f"SELECT * FROM {table}")
            return latest, rows
        if latest is None or version > latest or version < 0:
            raise FileNotFoundError(f"Version {version} not found for {layer}.{name}")
        try:
            rows = self._client.execute(f"SELECT * FROM {table} VERSION AS OF {version}")
        except DatabricksQueryError as exc:
            raise FileNotFoundError(f"Version {version} not found for {layer}.{name}") from exc
        return version, rows

    def _ensure_tables(self) -> None:
        bronze = self._table("bronze", "documents")
        silver = self._table("silver", "documents")
        gold_documents = self._table("gold", "documents")
        gold_counts = self._table("gold", "category_counts")
        self._client.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {bronze} (
                id STRING NOT NULL,
                title STRING,
                category STRING,
                content STRING,
                ingested_at STRING
            ) USING DELTA
            """
        )
        self._client.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {silver} (
                id STRING NOT NULL,
                title STRING,
                category STRING,
                content STRING,
                content_length BIGINT,
                ingested_at STRING
            ) USING DELTA
            """
        )
        self._client.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {gold_documents} (
                id STRING NOT NULL,
                title STRING,
                category STRING,
                content STRING,
                owner_team STRING
            ) USING DELTA
            """
        )
        self._client.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {gold_counts} (
                category STRING,
                `count` BIGINT
            ) USING DELTA
            """
        )

    def _overwrite_bronze(self, rows: list[dict[str, str]]) -> None:
        if not rows:
            self._client.execute(f"TRUNCATE TABLE {self._table('bronze', 'documents')}")
            return
        placeholders = []
        parameters: list[dict[str, str]] = []
        columns = ("id", "title", "category", "content", "ingested_at")
        for index, row in enumerate(rows):
            names = [f"{column}_{index}" for column in columns]
            placeholders.append("(" + ", ".join(f":{name}" for name in names) + ")")
            parameters.extend(
                {"name": name, "value": row[column], "type": "STRING"}
                for name, column in zip(names, columns, strict=True)
            )
        values_sql = ", ".join(placeholders)
        self._client.execute(
            f"""
            INSERT OVERWRITE {self._table("bronze", "documents")}
            (id, title, category, content, ingested_at)
            VALUES {values_sql}
            """,
            parameters,
        )

    def _count(self, table: str) -> int:
        rows = self._client.execute(f"SELECT COUNT(*) AS n FROM {table}")
        if not rows:
            return 0
        return int(rows[0]["n"])

    def _latest_version(self, table: str) -> int | None:
        history = self._client.execute(f"DESCRIBE HISTORY {table}")
        versions = [int(row["version"]) for row in history if "version" in row]
        if not versions:
            return None
        return max(versions)

    def _table(self, schema: str, name: str) -> str:
        return qualify(self._catalog, schema, name)


def _merge_silver(silver: str, bronze: str) -> str:
    return f"""
        MERGE INTO {silver} AS target
        USING (
            SELECT
                id,
                title,
                lower(category) AS category,
                content,
                length(content) AS content_length,
                ingested_at
            FROM {bronze}
            WHERE length(trim(content)) > 0 AND length(trim(title)) > 0
        ) AS source
        ON target.id = source.id
        WHEN MATCHED THEN UPDATE SET *
        WHEN NOT MATCHED THEN INSERT *
    """


def _owners_source() -> tuple[str, list[dict[str, str]]]:
    parts: list[str] = []
    parameters: list[dict[str, str]] = []
    for index, row in enumerate(OWNERS.rows):
        category_name = f"owner_category_{index}"
        team_name = f"owner_team_{index}"
        if index == 0:
            parts.append(f"SELECT :{category_name} AS category, :{team_name} AS owner_team")
        else:
            parts.append(f"SELECT :{category_name}, :{team_name}")
        parameters.append({"name": category_name, "value": str(row["category"]), "type": "STRING"})
        parameters.append({"name": team_name, "value": str(row["owner_team"]), "type": "STRING"})
    return " UNION ALL ".join(parts), parameters


def _overwrite_gold_documents(gold: str, silver: str, owners_sql: str) -> str:
    return f"""
        INSERT OVERWRITE {gold}
        SELECT source.id, source.title, source.category, source.content, owners.owner_team
        FROM {silver} AS source
        INNER JOIN ({owners_sql}) AS owners
            ON source.category = owners.category
    """


def _overwrite_category_counts(counts: str, silver: str) -> str:
    return f"""
        INSERT OVERWRITE {counts}
        SELECT category, COUNT(*) AS `count`
        FROM {silver}
        GROUP BY category
    """
