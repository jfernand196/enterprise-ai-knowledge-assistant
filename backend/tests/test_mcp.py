from fastapi.testclient import TestClient

from app.agent.tools import GetEmployeeProfileTool, GetVacationBalanceTool
from app.hr.repository import Employee, HrRepository
from app.mcp.client import McpClient
from app.mcp.server import McpServer


def test_list_mcp_tools_exposes_hr_capabilities(client: TestClient) -> None:
    response = client.get("/mcp/tools")

    assert response.status_code == 200
    names = {item["name"] for item in response.json()}
    assert names == {
        "get_employee_profile",
        "get_vacation_balance",
        "create_hr_request",
    }
    assert all(item["source"] == "mcp" for item in response.json())
    assert "search_documents" not in names


def test_mcp_client_calls_tool_through_server() -> None:
    repository = HrRepository(
        [Employee(user_id="emp-1", name="Juan Perez", department="Engineering", vacation_balance=8)]
    )
    client = McpClient(
        McpServer(
            [
                GetEmployeeProfileTool(repository),
                GetVacationBalanceTool(repository),
            ]
        )
    )

    result = client.call_tool("get_vacation_balance", {"user_id": "emp-1"})

    assert result == {"user_id": "emp-1", "vacation_balance": 8}


def test_mcp_client_returns_error_for_unknown_tool() -> None:
    client = McpClient(McpServer([]))

    result = client.call_tool("missing_tool", {})

    assert result["error"] == "Unknown tool: missing_tool"
