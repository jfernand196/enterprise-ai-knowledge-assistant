from pathlib import Path
from typing import Protocol

from app.lakehouse.databricks_client import DatabricksCliSqlClient
from app.lakehouse.databricks_pipeline import DatabricksLakehousePipeline
from app.lakehouse.pipeline import LakehousePipeline
from app.schemas.lakehouse import LakehouseRunResponse, LakehouseTableResponse


class LakehousePort(Protocol):
    def create_run(self) -> LakehouseRunResponse: ...

    def get_table(self, layer: str, name: str, version: int | None = None) -> LakehouseTableResponse: ...


class LakehouseService:
    def __init__(self, root: Path, documents_dir: Path) -> None:
        self._pipeline = LakehousePipeline(root)
        self._documents_dir = documents_dir

    def create_run(self) -> LakehouseRunResponse:
        result = self._pipeline.run(self._documents_dir)
        return LakehouseRunResponse.model_validate(result)

    def get_table(self, layer: str, name: str, version: int | None = None) -> LakehouseTableResponse:
        table = {
            ("bronze", "documents"): self._pipeline.bronze,
            ("silver", "documents"): self._pipeline.silver,
            ("gold", "documents"): self._pipeline.gold_documents,
            ("gold", "category_counts"): self._pipeline.gold_counts,
        }.get((layer, name))
        if table is None:
            raise KeyError(f"Unknown table: {layer}.{name}")
        rows = table.read(version)
        return LakehouseTableResponse(
            layer=layer,
            name=name,
            version=version if version is not None else table.latest_version(),
            rows=rows,
        )


class DatabricksLakehouseService:
    def __init__(
        self,
        documents_dir: Path,
        profile: str,
        warehouse_id: str,
        catalog: str,
    ) -> None:
        self._documents_dir = documents_dir
        self._pipeline = DatabricksLakehousePipeline(
            DatabricksCliSqlClient(profile, warehouse_id, catalog),
            catalog,
        )

    def create_run(self) -> LakehouseRunResponse:
        result = self._pipeline.run(self._documents_dir)
        return LakehouseRunResponse.model_validate(result)

    def get_table(self, layer: str, name: str, version: int | None = None) -> LakehouseTableResponse:
        resolved_version, rows = self._pipeline.read(layer, name, version)
        return LakehouseTableResponse(
            layer=layer,
            name=name,
            version=resolved_version,
            rows=rows,
        )


def build_lakehouse_service(
    backend: str,
    documents_dir: Path,
    lakehouse_dir: Path,
    profile: str,
    warehouse_id: str,
    catalog: str,
) -> LakehousePort:
    if backend == "local":
        return LakehouseService(lakehouse_dir, documents_dir)
    if backend == "databricks":
        return DatabricksLakehouseService(documents_dir, profile, warehouse_id, catalog)
    raise ValueError(f"Unknown lakehouse backend: {backend}")
