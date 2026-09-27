from dataclasses import dataclass
from typing import Any, Protocol

from app.core.text import truncate_excerpt
from app.hr.repository import EmployeeNotFoundError, HrRepository
from app.rag.retriever import Retriever


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: dict[str, str]


@dataclass(frozen=True)
class ToolObservation:
    name: str
    arguments: dict[str, str]
    result: dict[str, Any]


class ToolPort(Protocol):
    name: str

    def execute(self, arguments: dict[str, str]) -> dict[str, Any]: ...


class SearchDocumentsTool:
    name = "search_documents"

    def __init__(self, retriever: Retriever) -> None:
        self._retriever = retriever

    def execute(self, arguments: dict[str, str]) -> dict[str, Any]:
        query = arguments["query"]
        category = arguments.get("category") or None
        chunks = [item for item in self._retriever.retrieve(query, category=category) if item.score > 0]
        return {
            "documents": [
                {
                    "title": item.chunk.title,
                    "category": item.chunk.category,
                    "excerpt": truncate_excerpt(item.chunk.text),
                }
                for item in chunks
            ]
        }


class GetEmployeeProfileTool:
    name = "get_employee_profile"
    description = "Return an employee name and department."
    input_schema = {
        "type": "object",
        "required": ["user_id"],
        "properties": {"user_id": {"type": "string"}},
    }

    def __init__(self, repository: HrRepository) -> None:
        self._repository = repository

    def execute(self, arguments: dict[str, str]) -> dict[str, Any]:
        employee = self._repository.get_employee(arguments["user_id"])
        return {
            "user_id": employee.user_id,
            "name": employee.name,
            "department": employee.department,
        }


class GetVacationBalanceTool:
    name = "get_vacation_balance"
    description = "Return remaining vacation days for an employee."
    input_schema = {
        "type": "object",
        "required": ["user_id"],
        "properties": {"user_id": {"type": "string"}},
    }

    def __init__(self, repository: HrRepository) -> None:
        self._repository = repository

    def execute(self, arguments: dict[str, str]) -> dict[str, Any]:
        user_id = arguments["user_id"]
        return {
            "user_id": user_id,
            "vacation_balance": self._repository.get_vacation_balance(user_id),
        }


class CreateHrRequestTool:
    name = "create_hr_request"
    description = "Submit an HR request such as time off."
    input_schema = {
        "type": "object",
        "required": ["user_id"],
        "properties": {
            "user_id": {"type": "string"},
            "request_type": {"type": "string"},
            "details": {"type": "string"},
        },
    }

    def __init__(self, repository: HrRepository) -> None:
        self._repository = repository

    def execute(self, arguments: dict[str, str]) -> dict[str, Any]:
        record = self._repository.create_request(
            user_id=arguments["user_id"],
            request_type=arguments.get("request_type", "time_off"),
            details=arguments.get("details", ""),
        )
        return {
            "request_id": record.request_id,
            "status": record.status,
            "request_type": record.request_type,
        }


class ToolRegistry:
    def __init__(self, tools: list[ToolPort]) -> None:
        self._tools = {tool.name: tool for tool in tools}

    def execute(self, call: ToolCall) -> ToolObservation:
        tool = self._tools[call.name]
        try:
            result = tool.execute(call.arguments)
        except EmployeeNotFoundError:
            result = {"error": f"Unknown employee: {call.arguments.get('user_id')}"}
        return ToolObservation(name=call.name, arguments=call.arguments, result=result)
