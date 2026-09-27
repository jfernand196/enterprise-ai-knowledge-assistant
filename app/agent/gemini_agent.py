import json

from app.agent.answers import compose_answer
from app.agent.planner import KeywordPlanner
from app.agent.tools import ToolCall, ToolObservation
from app.rag.gemini import GeminiGroundedGenerator

ALLOWED_TOOLS = frozenset(
    {
        "get_employee_profile",
        "get_vacation_balance",
        "search_documents",
        "create_hr_request",
    }
)
USER_SCOPED_TOOLS = frozenset(
    {
        "get_employee_profile",
        "get_vacation_balance",
        "create_hr_request",
    }
)
PLAN_PROMPT = (
    "Decide whether an HR assistant needs tools. "
    "Company-wide policy questions do not need tools. "
    "Questions about the speaker's own profile, vacation balance, or a request they want submitted do. "
    "Reply with JSON only. "
    'Either {"needs_tools": false} or '
    '{"needs_tools": true, "calls": [{"name": "tool_name", "arguments": {}}]}. '
    "Allowed tools: get_employee_profile, get_vacation_balance, search_documents, create_hr_request. "
    "If they ask how many vacation days they have, call both get_employee_profile and get_vacation_balance. "
    "get_employee_profile and get_vacation_balance take user_id. "
    "search_documents takes query and optional category. Use it when they also need the policy text. "
    "create_hr_request takes user_id, request_type, and details, and only when the user asks to submit a request. "
    "Use the user_id provided in the message. Do not choose a different employee."
)
ANSWER_PROMPT = (
    "Write a short answer using only these tool results. "
    "If name is present, use it. If vacation_balance is present, state that exact number of vacation days left. "
    "If request_id and status are present, include both. "
    "If a result has an error, include that error and do not say the request succeeded. "
    "Do not invent numbers, names, or permissions. Do not ask for data that is already in the results."
)


class GeminiPlanner:
    def __init__(self, client: GeminiGroundedGenerator) -> None:
        self._client = client
        self._fallback = KeywordPlanner()
        self._cache: dict[str, list[ToolCall]] = {}

    def needs_tools(self, message: str) -> bool:
        self._client.last_usage = None
        try:
            return bool(self._calls(message))
        except (json.JSONDecodeError, TypeError, ValueError):
            return self._fallback.needs_tools(message)

    def plan(self, message: str, user_id: str | None) -> list[ToolCall]:
        if user_id is None:
            return []
        try:
            calls = self._calls(message)
        except (json.JSONDecodeError, TypeError, ValueError):
            return self._fallback.plan(message, user_id)
        return [_with_user(call, user_id, message) for call in calls]

    def _calls(self, message: str) -> list[ToolCall]:
        if message not in self._cache:
            raw = self._client.complete(PLAN_PROMPT, message)
            self._cache[message] = _parse_calls(raw)
        return self._cache[message]


class GeminiAnswerWriter:
    def __init__(self, client: GeminiGroundedGenerator) -> None:
        self._client = client

    @property
    def model_id(self) -> str:
        return self._client.model_id

    @property
    def last_usage(self) -> tuple[int, int] | None:
        return self._client.last_usage

    def write(self, question: str, observations: list[ToolObservation]) -> str:
        payload = [
            {"name": item.name, "result": item.result}
            for item in observations
        ]
        text = self._client.complete(
            ANSWER_PROMPT,
            f"Question: {question}\n\nTool results:\n{json.dumps(payload)}",
        )
        if not text.strip():
            return compose_answer(observations)
        for item in observations:
            error = item.result.get("error")
            if error and str(error) not in text:
                text = f"{error} {text}"
        return text.strip()


def _parse_calls(raw: str) -> list[ToolCall]:
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    data = json.loads(text)
    if not data.get("needs_tools"):
        return []
    calls: list[ToolCall] = []
    for item in data.get("calls") or []:
        name = str(item.get("name", ""))
        if name not in ALLOWED_TOOLS:
            continue
        arguments = {
            str(key): str(value)
            for key, value in dict(item.get("arguments") or {}).items()
        }
        calls.append(ToolCall(name, arguments))
    return calls


def _with_user(call: ToolCall, user_id: str, message: str) -> ToolCall:
    arguments = dict(call.arguments)
    if call.name in USER_SCOPED_TOOLS:
        arguments["user_id"] = user_id
    if call.name == "create_hr_request":
        arguments.setdefault("request_type", "time_off")
        arguments.setdefault("details", message)
    if call.name == "search_documents" and "query" not in arguments:
        arguments["query"] = message
    return ToolCall(call.name, arguments)
