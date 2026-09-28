from collections.abc import Callable
from typing import Any

from app.agent.tools import ToolObservation
from app.domain.models import Mode
from app.schemas.chat import ChatResponse, Citation, ToolCallResult

SEARCH_DOCUMENTS = "search_documents"
DEFAULT_ANSWER = "I could not complete that request."
MISSING_USER = "I can look that up, but I need a user_id to call the HR tools."

Formatter = Callable[[dict[str, Any]], str]


def _format_profile(result: dict[str, Any]) -> str:
    return f"{result['name']} works in {result['department']}."


def _format_vacation(result: dict[str, Any]) -> str:
    return f"You have {result['vacation_balance']} vacation days left."


def _format_hr_request(result: dict[str, Any]) -> str:
    return f"HR request {result['request_id']} was {result['status']}."


def _format_search(result: dict[str, Any]) -> str:
    documents = result.get("documents") or []
    if not documents:
        return ""
    first = documents[0]
    return f"According to {first['title']}: {first['excerpt']}"


FORMATTERS: dict[str, Formatter] = {
    "get_employee_profile": _format_profile,
    "get_vacation_balance": _format_vacation,
    "create_hr_request": _format_hr_request,
    SEARCH_DOCUMENTS: _format_search,
}


def compose_answer(observations: list[ToolObservation]) -> str:
    parts: list[str] = []
    for item in observations:
        if item.result.get("error"):
            parts.append(str(item.result["error"]))
            continue
        formatter = FORMATTERS.get(item.name)
        if formatter is None:
            continue
        text = formatter(item.result)
        if text:
            parts.append(text)
    return " ".join(parts) if parts else DEFAULT_ANSWER


def agent_response(request_id: str, message: str, answer: str, observations: list[ToolObservation]) -> ChatResponse:
    return ChatResponse.create(
        request_id=request_id,
        message=message,
        answer=answer,
        sources=sources_from(observations),
        citations=citations_from(observations),
        tool_calls=[
            ToolCallResult(name=item.name, arguments=item.arguments, result=item.result) for item in observations
        ],
        mode=Mode.AGENT,
    )


def sources_from(observations: list[ToolObservation]) -> list[str]:
    titles: list[str] = []
    for document in _search_documents(observations):
        if document["title"] not in titles:
            titles.append(document["title"])
    return titles


def citations_from(observations: list[ToolObservation]) -> list[Citation]:
    return [
        Citation(
            title=document["title"],
            doc_id=document["title"],
            category=document["category"],
            score=1.0,
            excerpt=document["excerpt"],
        )
        for document in _search_documents(observations)
    ]


def _search_documents(observations: list[ToolObservation]) -> list[dict[str, Any]]:
    documents: list[dict[str, Any]] = []
    for item in observations:
        if item.name != SEARCH_DOCUMENTS:
            continue
        documents.extend(item.result.get("documents") or [])
    return documents
