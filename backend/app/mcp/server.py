from typing import Any

from app.agent.tools import ToolPort
from app.hr.repository import EmployeeNotFoundError
from app.mcp.protocol import McpRequest, McpResponse, McpToolSpec


class McpServer:
    """Exposes tools through MCP-style tools/list and tools/call.

    The transport is in-process here. In production this server would
    sit behind stdio or SSE and the AI app would only know the client.
    """

    def __init__(self, tools: list[ToolPort]) -> None:
        self._tools = {tool.name: tool for tool in tools}

    def handle(self, request: McpRequest) -> McpResponse:
        if request.method == "tools/list":
            return McpResponse(result=[spec.__dict__ for spec in self.list_tools()])
        if request.method == "tools/call":
            name = request.params["name"]
            arguments = request.params.get("arguments") or {}
            try:
                return McpResponse(result=self.call_tool(name, arguments))
            except KeyError:
                return McpResponse(result=None, error=f"Unknown tool: {name}")
            except EmployeeNotFoundError:
                user_id = arguments.get("user_id")
                return McpResponse(result={"error": f"Unknown employee: {user_id}"})
        return McpResponse(result=None, error=f"Unknown method: {request.method}")

    def list_tools(self) -> list[McpToolSpec]:
        return [
            McpToolSpec(
                name=tool.name,
                description=getattr(tool, "description", tool.name),
                input_schema=getattr(tool, "input_schema", {"type": "object"}),
            )
            for tool in self._tools.values()
        ]

    def call_tool(self, name: str, arguments: dict[str, str]) -> dict[str, Any]:
        return self._tools[name].execute(arguments)
