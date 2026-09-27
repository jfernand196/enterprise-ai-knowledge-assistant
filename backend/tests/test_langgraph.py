from typing import Any

import pytest
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage

from app.agent.tools import CreateHrRequestTool, GetEmployeeProfileTool, GetVacationBalanceTool, ToolRegistry
from app.core.config import PROJECT_ROOT, settings
from app.hr.repository import HrRepository
from app.knowledge.index import build_knowledge_index
from app.lg.service import build_langgraph_service
from app.lg.tools import build_graph_tools
from app.schemas.chat import ChatRequest


class ToolFakeModel(FakeMessagesListChatModel):
    def bind_tools(self, tools: Any, **kwargs: Any) -> "ToolFakeModel":
        return self


class FixedRouter:
    def __init__(self, needs_tools: bool) -> None:
        self._needs_tools = needs_tools

    def needs_tools(self, message: str) -> bool:
        return self._needs_tools


def _retriever():
    return build_knowledge_index(
        documents_dir=PROJECT_ROOT / "data" / "documents",
        chunk_size=settings.chunk_size,
        overlap=settings.chunk_overlap,
        top_k=3,
    ).retriever


def _registry() -> ToolRegistry:
    repository = HrRepository.from_json(settings.employees_path)
    return ToolRegistry(
        [GetEmployeeProfileTool(repository), GetVacationBalanceTool(repository), CreateHrRequestTool(repository)]
    )


def _service(responses: list[AIMessage], needs_tools: bool):
    return build_langgraph_service(
        _retriever(),
        _registry(),
        frozenset({"emp-2"}),
        gemini_api_key="",
        model_id="",
        groq_api_key="",
        groq_model_id="",
        models=[ToolFakeModel(responses=responses)],
        router=FixedRouter(needs_tools),
    )


def _submit_then(final_text: str) -> list[AIMessage]:
    return [
        AIMessage(
            content="",
            tool_calls=[{"name": "create_hr_request", "args": {"request_type": "time_off"}, "id": "call-1"}],
            usage_metadata={"input_tokens": 300, "output_tokens": 10, "total_tokens": 310},
        ),
        AIMessage(content=final_text, usage_metadata={"input_tokens": 350, "output_tokens": 15, "total_tokens": 365}),
    ]


def test_injected_state_hides_user_id_from_the_model() -> None:
    tools = {tool.name: tool for tool in build_graph_tools(_registry(), frozenset({"emp-2"}))}

    visible = tools["create_hr_request"].tool_call_schema.model_json_schema()["properties"]

    assert "user_id" not in visible
    assert "question" not in visible
    assert "request_type" in visible


@pytest.mark.asyncio
async def test_policy_question_takes_the_rag_branch() -> None:
    service = _service([AIMessage(content="Vacation Policy: 15 days, up to 5 carried over.")], needs_tools=False)

    response = await service.answer(ChatRequest(message="What is the vacation policy?"), "req-1")

    assert response.mode == "rag"
    assert "Vacation Policy" in response.sources
    assert response.tool_calls == []


@pytest.mark.asyncio
async def test_agent_loop_sums_tokens_across_turns() -> None:
    service = _service(_submit_then("Your request was submitted."), needs_tools=True)

    response = await service.answer(
        ChatRequest(message="Please submit a time off request for next Friday", user_id="emp-2"), "req-2"
    )

    assert response.mode == "agent"
    assert response.tool_calls[0].arguments["user_id"] == "emp-2"
    assert "request_id" in response.tool_calls[0].result
    assert (response.input_tokens, response.output_tokens) == (650, 25)


@pytest.mark.asyncio
async def test_agent_keeps_authorization_errors() -> None:
    service = _service(_submit_then("Done!"), needs_tools=True)

    response = await service.answer(
        ChatRequest(message="Please submit a time off request for next Friday", user_id="emp-1"), "req-3"
    )

    assert "not allowed" in response.answer
    assert response.tool_calls[0].result["error"].startswith("User emp-1")


@pytest.mark.asyncio
async def test_agent_without_user_stops_before_calling_the_model() -> None:
    service = _service([], needs_tools=True)

    response = await service.answer(ChatRequest(message="How many vacation days do I have left?"), "req-4")

    assert "user_id" in response.answer
