import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_lakehouse_service
from app.lakehouse.databricks_client import DatabricksQueryError
from app.schemas.lakehouse import LakehouseRunResponse, LakehouseTableResponse
from app.services.lakehouse_service import LakehousePort

router = APIRouter()


@router.post("/lakehouse/runs", response_model=LakehouseRunResponse)
async def create_lakehouse_run(
    service: Annotated[LakehousePort, Depends(get_lakehouse_service)],
) -> LakehouseRunResponse:
    try:
        return await asyncio.to_thread(service.create_run)
    except DatabricksQueryError as exc:
        raise HTTPException(status_code=502, detail=exc.message) from exc


@router.get(
    "/lakehouse/tables/{layer}/{name}",
    response_model=LakehouseTableResponse,
)
async def get_lakehouse_table(
    layer: str,
    name: str,
    service: Annotated[LakehousePort, Depends(get_lakehouse_service)],
    version: int | None = None,
) -> LakehouseTableResponse:
    try:
        return await asyncio.to_thread(service.get_table, layer, name, version)
    except (KeyError, FileNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DatabricksQueryError as exc:
        raise HTTPException(status_code=502, detail=exc.message) from exc
