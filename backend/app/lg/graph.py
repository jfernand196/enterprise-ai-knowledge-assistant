import asyncio
import json

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import BaseTool
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from app.agent.gemini_agent import USER_SCOPED_TOOLS
from app.agent.tools import ToolObservation
from app.lc.agent import keep_errors
from app.lc.models import model_name, token_usage, with_fallbacks
from app.lc.rag_chain import RAG_PROMPT, format_documents
from app.lc.retriever import IndexRetriever
from app.lc.services import MISSING_USER, RouterPort
from app.lg.state import GraphState
from app.rag.generator import NO_CONTEXT_ANSWER
from app.rag.retriever import Retriever


def build_graph(
    retriever: Retriever,
    models: list[BaseChatModel],
    router: RouterPort,
    tools: list[BaseTool],
) -> CompiledStateGraph:
    """route -> retrieve -> generate          (policy question)
       route -> agent <-> tools -> finish     (question about the caller)

    Each node is a function: it receives the state and returns only the
    keys it changes. Conditional edges read the state to pick the next node.
    """
    answer_model = with_fallbacks(models)
    agent_model = with_fallbacks(models, tools)

    async def route(state: GraphState) -> dict:
        needs_tools = await asyncio.to_thread(router.needs_tools, state["question"])
        return {"route": "agent" if needs_tools else "rag"}

    async def retrieve(state: GraphState) -> dict:
        index = IndexRetriever(retriever=retriever, category=state.get("category"), top_k=state.get("top_k"))
        return {"documents": await index.ainvoke(state["question"])}

    async def generate(state: GraphState) -> dict:
        message = await (RAG_PROMPT | answer_model).ainvoke(
            {"question": state["question"], "context": format_documents(state["documents"])}
        )
        return _answer_update(message, message.text.strip())

    async def agent(state: GraphState) -> dict:
        reply = await agent_model.ainvoke(state["messages"])
        update = _answer_update(reply, "")
        update["messages"] = [reply]
        return update

    def finish(state: GraphState) -> dict:
        last = state["messages"][-1]
        observations = observations_from(state["messages"], state.get("user_id"))
        return {"answer": keep_errors(last.text.strip(), observations)}

    graph = StateGraph(GraphState)
    graph.add_node("route", route)
    graph.add_node("retrieve", retrieve)
    graph.add_node("generate", generate)
    graph.add_node("no_context", lambda _: {"answer": NO_CONTEXT_ANSWER})
    graph.add_node("missing_user", lambda _: {"answer": MISSING_USER})
    graph.add_node("agent", agent)
    graph.add_node("tools", ToolNode(tools))
    graph.add_node("finish", finish)

    graph.add_edge(START, "route")
    graph.add_conditional_edges("route", _after_route, ["retrieve", "agent", "missing_user"])
    graph.add_conditional_edges("retrieve", _after_retrieve, ["generate", "no_context"])
    graph.add_conditional_edges("agent", tools_condition, {"tools": "tools", END: "finish"})
    graph.add_edge("tools", "agent")
    for node in ("generate", "no_context", "missing_user", "finish"):
        graph.add_edge(node, END)
    return graph.compile()


def observations_from(messages: list, user_id: str | None) -> list[ToolObservation]:
    """Pair each ToolMessage with the tool call that produced it."""
    calls = {
        call["id"]: call
        for message in messages
        if isinstance(message, AIMessage)
        for call in message.tool_calls
    }
    observations: list[ToolObservation] = []
    for message in messages:
        if not isinstance(message, ToolMessage):
            continue
        call = calls.get(message.tool_call_id, {})
        arguments = {key: str(value) for key, value in (call.get("args") or {}).items()}
        if message.name in USER_SCOPED_TOOLS and user_id:
            arguments["user_id"] = user_id
        observations.append(ToolObservation(name=message.name, arguments=arguments, result=_parse(message.content)))
    return observations


def _after_route(state: GraphState) -> str:
    if state["route"] == "rag":
        return "retrieve"
    return "agent" if state.get("user_id") else "missing_user"


def _after_retrieve(state: GraphState) -> str:
    return "generate" if state["documents"] else "no_context"


def _answer_update(message: AIMessage, answer: str) -> dict:
    input_tokens, output_tokens = token_usage(message)
    return {
        "answer": answer,
        "model": model_name(message),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    }


def _parse(content: object) -> dict:
    try:
        parsed = json.loads(content) if isinstance(content, str) else content
    except json.JSONDecodeError:
        return {"error": str(content)}
    return parsed if isinstance(parsed, dict) else {"result": parsed}
