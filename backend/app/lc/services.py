from typing import Protocol

from langchain_core.documents import Document
from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import Runnable

from app.agent.answers import MISSING_USER, agent_response, compose_answer
from app.agent.tools import ToolRegistry
from app.core.text import truncate_excerpt
from app.domain.models import Mode
from app.lc.agent import keep_errors, run_tool_agent
from app.lc.models import build_chat_models, model_name, token_usage, with_fallbacks
from app.lc.rag_chain import build_rag_chain
from app.lc.retriever import IndexRetriever
from app.lc.router import StructuredRouter
from app.lc.tools import ScopedTools
from app.rag.retriever import Retriever
from app.schemas.chat import ChatRequest, ChatResponse, Citation


class RouterPort(Protocol):
    def needs_tools(self, message: str) -> bool: ...


class LangChainRagService:
    def __init__(self, retriever: Retriever, model: Runnable) -> None:
        self._retriever = retriever
        self._model = model

    async def answer(self, payload: ChatRequest, request_id: str) -> ChatResponse:
        chain = build_rag_chain(
            IndexRetriever(retriever=self._retriever, category=payload.category, top_k=payload.top_k),
            self._model,
        )
        state = await chain.ainvoke(payload.message)
        documents: list[Document] = state["documents"]
        message = state["message"]
        response = rag_response(request_id, payload.message, message.text.strip(), documents)
        if documents:
            response.model = model_name(message)
            response.input_tokens, response.output_tokens = token_usage(message)
        return response


class LangChainAgentService:
    def __init__(
        self,
        registry: ToolRegistry,
        models: list[BaseChatModel],
        router: RouterPort,
        writers: frozenset[str],
    ) -> None:
        self._registry = registry
        self._models = models
        self._router = router
        self._writers = writers

    def needs_tools(self, message: str) -> bool:
        return self._router.needs_tools(message)

    async def answer(self, payload: ChatRequest, request_id: str) -> ChatResponse:
        if payload.user_id is None:
            return agent_response(request_id, payload.message, MISSING_USER, [])
        scoped = ScopedTools(self._registry, payload.user_id, self._writers, payload.message)
        tools = scoped.build()
        run = await run_tool_agent(with_fallbacks(self._models, tools), tools, payload.message)
        observations = scoped.observations
        answer = keep_errors(run.answer or compose_answer(observations), observations)
        response = agent_response(request_id, payload.message, answer, observations)
        response.model = run.model
        response.input_tokens, response.output_tokens = run.input_tokens, run.output_tokens
        return response


def build_langchain_services(
    retriever: Retriever,
    registry: ToolRegistry,
    writers: frozenset[str],
    gemini_api_key: str,
    model_id: str,
    groq_api_key: str,
    groq_model_id: str,
) -> tuple[LangChainRagService, LangChainAgentService]:
    models = build_chat_models(gemini_api_key, model_id, groq_api_key, groq_model_id)
    if not models:
        raise ValueError("ORCHESTRATOR=langchain needs GEMINI_API_KEY or GROQ_API_KEY.")
    return (
        LangChainRagService(retriever, with_fallbacks(models)),
        LangChainAgentService(registry, models, StructuredRouter(models), writers),
    )


def rag_response(request_id: str, message: str, answer: str, documents: list[Document]) -> ChatResponse:
    return ChatResponse.create(
        request_id=request_id,
        message=message,
        answer=answer,
        sources=list(dict.fromkeys(document.metadata["title"] for document in documents)),
        citations=[to_citation(document) for document in documents],
        mode=Mode.RAG,
    )


def to_citation(document: Document) -> Citation:
    return Citation(
        title=document.metadata["title"],
        doc_id=document.metadata["doc_id"],
        category=document.metadata["category"],
        score=document.metadata["score"],
        excerpt=truncate_excerpt(document.page_content),
    )
