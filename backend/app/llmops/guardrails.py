
INJECTION_PATTERNS = (
    "ignore previous instructions",
    "ignore all previous",
    "disregard previous",
    "reveal the system prompt",
    "reveal your system prompt",
    "you are now",
)

WRITE_TOOLS = frozenset({"create_hr_request"})


class GuardrailRejectedError(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def check_input(message: str) -> None:
    lowered = message.lower()
    if any(pattern in lowered for pattern in INJECTION_PATTERNS):
        raise GuardrailRejectedError("Prompt injection detected")


def check_output(answer: str) -> str:
    lowered = answer.lower()
    if "system prompt" in lowered:
        return "The response was blocked by output validation."
    return answer


def authorize_tool(tool_name: str, user_id: str | None, writers: frozenset[str]) -> str | None:
    if tool_name not in WRITE_TOOLS:
        return None
    if user_id in writers:
        return None
    return f"User {user_id} is not allowed to execute {tool_name}"
