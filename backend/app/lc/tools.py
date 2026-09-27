from typing import Any

from langchain_core.tools import BaseTool, StructuredTool

from app.agent.tools import ToolCall, ToolObservation, ToolRegistry
from app.llmops.guardrails import authorize_tool


class ScopedTools:
    """LangChain tools for one request, bound to the caller's user_id.

    The model never sees a user_id argument, so it cannot ask for another
    employee. Every call still goes through authorize_tool and the same
    ToolRegistry (and MCP client) the native agent uses.
    """

    def __init__(self, registry: ToolRegistry, user_id: str, writers: frozenset[str], message: str) -> None:
        self._registry = registry
        self._user_id = user_id
        self._writers = writers
        self._message = message
        self.observations: list[ToolObservation] = []

    def build(self) -> list[BaseTool]:
        return [
            StructuredTool.from_function(
                self.get_employee_profile,
                name="get_employee_profile",
                description="Return the caller's name and department.",
            ),
            StructuredTool.from_function(
                self.get_vacation_balance,
                name="get_vacation_balance",
                description="Return how many vacation days the caller has left.",
            ),
            StructuredTool.from_function(
                self.search_documents,
                name="search_documents",
                description="Search company policy documents. category is one of hr, security, product, customer.",
            ),
            StructuredTool.from_function(
                self.create_hr_request,
                name="create_hr_request",
                description="Submit an HR request for the caller, such as time off. Only when the caller asks to submit one.",
            ),
        ]

    def get_employee_profile(self) -> dict[str, Any]:
        return self._run("get_employee_profile", {"user_id": self._user_id})

    def get_vacation_balance(self) -> dict[str, Any]:
        return self._run("get_vacation_balance", {"user_id": self._user_id})

    def search_documents(self, query: str, category: str | None = None) -> dict[str, Any]:
        arguments = {"query": query}
        if category:
            arguments["category"] = category
        return self._run("search_documents", arguments)

    def create_hr_request(self, request_type: str = "time_off", details: str = "") -> dict[str, Any]:
        return self._run(
            "create_hr_request",
            {
                "user_id": self._user_id,
                "request_type": request_type,
                "details": details or self._message,
            },
        )

    def _run(self, name: str, arguments: dict[str, str]) -> dict[str, Any]:
        denied = authorize_tool(name, self._user_id, self._writers)
        if denied:
            observation = ToolObservation(name=name, arguments=arguments, result={"error": denied})
        else:
            observation = self._registry.execute(ToolCall(name, arguments))
        self.observations.append(observation)
        return observation.result
