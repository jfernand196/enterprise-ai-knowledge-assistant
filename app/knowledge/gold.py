from app.domain.models import Document
from app.lakehouse.databricks_client import DatabricksQueryError, SqlClient
from app.lakehouse.identifiers import qualify


def load_gold_documents(client: SqlClient, catalog: str) -> list[Document]:
    table = qualify(catalog, "gold", "documents")
    rows = client.execute(f"SELECT id, title, category, content FROM {table}")
    if not rows:
        raise DatabricksQueryError(f"{table} is empty. Run POST /lakehouse/runs first.")
    return [
        Document(
            doc_id=str(row["id"]),
            title=str(row["title"]),
            category=str(row["category"]),
            content=str(row["content"]),
        )
        for row in rows
    ]
