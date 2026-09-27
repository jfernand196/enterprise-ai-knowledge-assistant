from typing import Any

from pydantic import BaseModel


class LakehouseRunResponse(BaseModel):
    bronze_rows: int
    silver_rows: int
    gold_documents: int
    category_counts: list[dict[str, Any]]
    versions: dict[str, int]


class LakehouseTableResponse(BaseModel):
    layer: str
    name: str
    version: int | None
    rows: list[dict[str, Any]]
