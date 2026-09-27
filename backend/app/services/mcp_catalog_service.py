from app.mcp.client import McpClient
from app.schemas.mcp import McpToolResponse


class McpCatalogService:
    def __init__(self, client: McpClient) -> None:
        self._client = client

    def list_tools(self) -> list[McpToolResponse]:
        return [
            McpToolResponse(
                name=spec.name,
                description=spec.description,
                input_schema=spec.input_schema,
                source="mcp",
            )
            for spec in self._client.list_tools()
        ]
