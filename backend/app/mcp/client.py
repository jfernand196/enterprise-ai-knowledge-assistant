from typing import Any

from app.mcp.protocol import McpRequest, McpResponse, McpToolSpec
from app.mcp.server import McpServer


class McpClient:
    def __init__(self, server: McpServer) -> None:
        self._server = server

    def list_tools(self) -> list[McpToolSpec]:
        response = self._request("tools/list", {})
        return [McpToolSpec(**item) for item in response.result]

    def call_tool(self, name: str, arguments: dict[str, str]) -> dict[str, Any]:
        response = self._request("tools/call", {"name": name, "arguments": arguments})
        if response.error:
            return {"error": response.error}
        return response.result

    def _request(self, method: str, params: dict[str, Any]) -> McpResponse:
        return self._server.handle(McpRequest(method=method, params=params))


class McpToolAdapter:
    """Lets the agent treat a remote MCP tool as a local ToolPort."""

    def __init__(self, client: McpClient, spec: McpToolSpec) -> None:
        self.name = spec.name
        self.description = spec.description
        self.input_schema = spec.input_schema
        self._client = client

    def execute(self, arguments: dict[str, str]) -> dict[str, Any]:
        return self._client.call_tool(self.name, arguments)
