from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_mcp_catalog_service
from app.schemas.mcp import McpToolResponse
from app.services.mcp_catalog_service import McpCatalogService

router = APIRouter()


@router.get("/mcp/tools", response_model=list[McpToolResponse])
async def list_mcp_tools(
    service: Annotated[McpCatalogService, Depends(get_mcp_catalog_service)],
) -> list[McpToolResponse]:
    return service.list_tools()
