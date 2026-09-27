from typing import Any

import pytest
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage

from app.agent.tools import GetEmployeeProfileTool, GetVacationBalanceTool, CreateHrRequestTool, ToolRegistry
from app.core.config import PROJECT_ROOT, settings
from app.hr.repository import HrRepository
from app.knowledge.index import build_knowledge_index
from app.lc.retriever import IndexRetriever
from app.lc.services import LangChainAgentService, LangChainRagService
from app.rag.generator import NO_CONTEXT_ANSWER
from app.schemas.chat import ChatRequest


class ToolFakeModel(FakeMessagesListChatModel):
    """Scripted replies; bind_tools is a no-op so the agent loop can run offline."""

    def bind_tools(self, tools: Any, **kwargs: Any) -> "ToolFakeModel":
        return self


class AlwaysTools:
    def needs_tools(self, message: str) -> bool:
        return True


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
        [
            GetEmployeeProfileTool(repository),
            GetVacationBalanceTool(repository),
            CreateHrRequestTool(repository),
        ]
    )


def test_index_retriever_returns_langchain_documents() -> None:
    documents = IndexRetriever(retriever=_retriever()).invoke("How many vacation days do employees receive?")

    assert documents[0].metadata["title"] == "Vacation Policy"
    assert "15 paid vacation days" in documents[0].page_content


@pytest.mark.asyncio
async def test_rag_chain_reports_answer_model_and_tokens() -> None:
    model = ToolFakeModel(
        responses=[
            AIMessage(
                content="The Vacation Policy gives 15 days, and up to 5 days may be carried over.",
                response_metadata={"model_name": "fake-flash"},
                usage_metadata={"input_tokens": 600, "output_tokens": 20, "total_tokens": 620},
            )
        ]
    )

    response = await LangChainRagService(_retriever(), model).answer(
        ChatRequest(message="What is the vacation policy?"), "req-1"
    )

    assert "5 days" in response.answer
    assert "Vacation Policy" in response.sources
    assert response.model == "fake-flash"
    assert (response.input_tokens, response.output_tokens) == (600, 20)


@pytest.mark.asyncio
async def test_rag_chain_skips_the_model_without_context() -> None:
    model = ToolFakeModel(responses=[])

    response = await LangChainRagService(_retriever(), model).answer(
        ChatRequest(message="zzzz qqqq"), "req-2"
    )

    assert response.answer == NO_CONTEXT_ANSWER
    assert response.citations == []


def _request_then_answer(final_text: str) -> ToolFakeModel:
    return ToolFakeModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "create_hr_request",
                        "args": {"request_type": "time_off", "details": "next Friday"},
                        "id": "call-1",
                    }
                ],
            ),
            AIMessage(content=final_text),
        ]
    )


@pytest.mark.asyncio
async def test_agent_lets_hr_writers_create_requests() -> None:
    service = LangChainAgentService(
        _registry(), [_request_then_answer("Your request was submitted.")], AlwaysTools(), frozenset({"emp-2"})
    )

    response = await service.answer(
        ChatRequest(message="Please submit a time off request for next Friday", user_id="emp-2"), "req-3"
    )

    assert response.tool_calls[0].name == "create_hr_request"
    assert response.tool_calls[0].arguments["user_id"] == "emp-2"
    assert "request_id" in response.tool_calls[0].result


@pytest.mark.asyncio
async def test_agent_keeps_the_authorization_error_even_if_the_model_hides_it() -> None:
    service = LangChainAgentService(
        _registry(), [_request_then_answer("Done!")], AlwaysTools(), frozenset({"emp-2"})
    )

    response = await service.answer(
        ChatRequest(message="Please submit a time off request for next Friday", user_id="emp-1"), "req-4"
    )

    assert "not allowed" in response.answer
    assert response.tool_calls[0].result["error"].startswith("User emp-1")
