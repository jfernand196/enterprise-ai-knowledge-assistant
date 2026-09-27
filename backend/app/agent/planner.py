from typing import Protocol

from app.agent.tools import ToolCall

PERSONAL_MARKERS = (
    " my ",
    "i have",
    "do i have",
    "left",
    "balance",
    "profile",
    "submit",
    "create a request",
    "open a request",
    "time off request",
)


class PlannerPort(Protocol):
    def needs_tools(self, message: str) -> bool: ...
    def plan(self, message: str, user_id: str | None) -> list[ToolCall]: ...


class KeywordPlanner:
    """Deterministic stand-in for LLM tool calling.

    Same AgentPort contract. Later swap for model-driven function calling.
    """

    def needs_tools(self, message: str) -> bool:
        normalized = f" {message.lower()} "
        return any(marker in normalized for marker in PERSONAL_MARKERS)

    def plan(self, message: str, user_id: str | None) -> list[ToolCall]:
        if user_id is None:
            return []

        text = message.lower()
        calls: list[ToolCall] = [
            ToolCall("get_employee_profile", {"user_id": user_id}),
        ]
        if _asks_for_balance(text):
            calls.append(ToolCall("get_vacation_balance", {"user_id": user_id}))
            calls.append(
                ToolCall("search_documents", {"query": "vacation policy", "category": "hr"})
            )
        if _asks_to_create_request(text):
            calls.append(
                ToolCall(
                    "create_hr_request",
                    {
                        "user_id": user_id,
                        "request_type": "time_off",
                        "details": message,
                    },
                )
            )
        return calls


def _asks_for_balance(text: str) -> bool:
    return any(token in text for token in ("left", "balance", "how many", "do i have"))


def _asks_to_create_request(text: str) -> bool:
    return any(
        token in text
        for token in ("submit", "create a request", "open a request", "time off request")
    )
