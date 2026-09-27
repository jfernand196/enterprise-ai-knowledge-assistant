from typing import Annotated, Any

from langchain_core.tools import BaseTool, tool
from langgraph.prebuilt import InjectedState

from app.agent.tools import ToolCall, ToolRegistry
from app.llmops.guardrails import authorize_tool


def build_graph_tools(registry: ToolRegistry, writers: frozenset[str]) -> list[BaseTool]:
    """Tools built once for the whole graph.

    InjectedState("user_id") fills the argument from the graph state when
    ToolNode runs the tool. It is left out of the schema the model sees,
    so the model cannot choose another employee.
    """

    def run(name: str, user_id: str | None, arguments: dict[str, str]) -> dict[str, Any]:
        denied = authorize_tool(name, user_id, writers)
        if denied:
            return {"error": denied}
        return registry.execute(ToolCall(name, arguments)).result

    @tool
    def get_employee_profile(user_id: Annotated[str, InjectedState("user_id")]) -> dict[str, Any]:
        """Return the caller's name and department."""
        return run("get_employee_profile", user_id, {"user_id": user_id})

    @tool
    def get_vacation_balance(user_id: Annotated[str, InjectedState("user_id")]) -> dict[str, Any]:
        """Return how many vacation days the caller has left."""
        return run("get_vacation_balance", user_id, {"user_id": user_id})

    @tool
    def search_documents(query: str, category: str | None = None) -> dict[str, Any]:
        """Search company policy documents. category is one of hr, security, product, customer."""
        arguments = {"query": query}
        if category:
            arguments["category"] = category
        return run("search_documents", None, arguments)

    @tool
    def create_hr_request(
        user_id: Annotated[str, InjectedState("user_id")],
        question: Annotated[str, InjectedState("question")],
        request_type: str = "time_off",
        details: str = "",
    ) -> dict[str, Any]:
        """Submit an HR request for the caller, such as time off. Only when the caller asks to submit one."""
        return run(
            "create_hr_request",
            user_id,
            {"user_id": user_id, "request_type": request_type, "details": details or question},
        )

    return [get_employee_profile, get_vacation_balance, search_documents, create_hr_request]
