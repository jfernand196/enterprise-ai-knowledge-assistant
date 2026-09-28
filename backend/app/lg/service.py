from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.errors import GraphRecursionError
from langgraph.graph.state import CompiledStateGraph

from app.agent.answers import DEFAULT_ANSWER, agent_response
from app.agent.tools import ToolRegistry
from app.domain.models import Mode
from app.lc.agent import AGENT_PROMPT
from app.lc.models import build_chat_models
from app.lc.router import StructuredRouter
from app.lc.services import RouterPort, rag_response
from app.lg.graph import build_graph, observations_from
from app.lg.state import GraphState
from app.lg.tools import build_graph_tools
from app.rag.retriever import Retriever
from app.schemas.chat import ChatRequest, ChatResponse

RECURSION_LIMIT = 12


class LangGraphService:
    """Runs the whole question through one graph: routing, RAG, and the agent loop."""

    def __init__(self, graph: CompiledStateGraph) -> None:
        self._graph = graph

    async def answer(self, payload: ChatRequest, request_id: str) -> ChatResponse:
        try:
            state = await self._graph.ainvoke(initial_state(payload), config={"recursion_limit": RECURSION_LIMIT})
        except GraphRecursionError:
            return agent_response(request_id, payload.message, DEFAULT_ANSWER, [])
        if state["route"] == Mode.RAG:
            response = rag_response(request_id, payload.message, state["answer"], state.get("documents") or [])
        else:
            observations = observations_from(state["messages"], payload.user_id)
            response = agent_response(request_id, payload.message, state["answer"], observations)
        if state.get("model"):
            response.model = state["model"]
        response.input_tokens = state.get("input_tokens", 0)
        response.output_tokens = state.get("output_tokens", 0)
        return response


def initial_state(payload: ChatRequest) -> GraphState:
    return {
        "question": payload.message,
        "user_id": payload.user_id,
        "category": payload.category,
        "top_k": payload.top_k,
        "route": "",
        "documents": [],
        "messages": [SystemMessage(AGENT_PROMPT), HumanMessage(payload.message)],
        "answer": "",
        "model": "",
        "input_tokens": 0,
        "output_tokens": 0,
    }


def build_langgraph_service(
    retriever: Retriever,
    registry: ToolRegistry,
    writers: frozenset[str],
    gemini_api_key: str,
    model_id: str,
    groq_api_key: str,
    groq_model_id: str,
    models: list[BaseChatModel] | None = None,
    router: RouterPort | None = None,
) -> LangGraphService:
    models = models or build_chat_models(gemini_api_key, model_id, groq_api_key, groq_model_id)
    if not models:
        raise ValueError("ORCHESTRATOR=langgraph needs GEMINI_API_KEY or GROQ_API_KEY.")
    graph = build_graph(retriever, models, router or StructuredRouter(models), build_graph_tools(registry, writers))
    return LangGraphService(graph)
