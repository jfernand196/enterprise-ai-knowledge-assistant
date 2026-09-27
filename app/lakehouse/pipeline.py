from datetime import UTC, datetime
from pathlib import Path

from app.knowledge.loader import load_documents
from app.lakehouse.delta import DeltaTable
from app.lakehouse.frame import Frame, sql_count_by_category

OWNERS = Frame(
    [
        {"category": "hr", "owner_team": "People"},
        {"category": "security", "owner_team": "Security"},
        {"category": "product", "owner_team": "Product"},
        {"category": "customer", "owner_team": "Support"},
    ]
)


class LakehousePipeline:
    def __init__(self, root: Path) -> None:
        self.bronze = DeltaTable(root / "bronze", "documents")
        self.silver = DeltaTable(root / "silver", "documents")
        self.gold_documents = DeltaTable(root / "gold", "documents")
        self.gold_counts = DeltaTable(root / "gold", "category_counts")

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
        bronze_version = self.bronze.write(bronze_rows)

        silver_frame = (
            Frame(bronze_rows)
            .filter(lambda row: bool(row["content"].strip()))
            .filter(lambda row: bool(row["title"].strip()))
        )
        silver_rows = [
            {
                **row,
                "category": row["category"].lower(),
                "content_length": len(row["content"]),
            }
            for row in silver_frame.rows
        ]
        silver_version = self.silver.merge(silver_rows, key="id")

        gold_docs = Frame(silver_rows).join(OWNERS, on="category").select(
            "id",
            "title",
            "category",
            "content",
            "owner_team",
        )
        gold_doc_version = self.gold_documents.write(gold_docs.rows)
        counts = sql_count_by_category(Frame(silver_rows))
        gold_count_version = self.gold_counts.write(counts.rows)

        return {
            "bronze_rows": len(bronze_rows),
            "silver_rows": len(silver_rows),
            "gold_documents": len(gold_docs.rows),
            "category_counts": counts.rows,
            "versions": {
                "bronze.documents": bronze_version,
                "silver.documents": silver_version,
                "gold.documents": gold_doc_version,
                "gold.category_counts": gold_count_version,
            },
        }
