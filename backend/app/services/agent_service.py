import asyncio

from app.agent.answers import MISSING_USER, agent_response, compose_answer
from app.agent.planner import KeywordPlanner, PlannerPort
from app.agent.tools import ToolCall, ToolObservation, ToolRegistry
from app.llmops.guardrails import authorize_tool
from app.schemas.chat import ChatRequest, ChatResponse


class AgentService:
    def __init__(
        self,
        registry: ToolRegistry,
        planner: PlannerPort | None = None,
        writers: frozenset[str] | None = None,
        answer_writer: object | None = None,
    ) -> None:
        self._registry = registry
        self._planner = planner or KeywordPlanner()
        self._writers = writers if writers is not None else frozenset()
        self._answer_writer = answer_writer

    def needs_tools(self, message: str) -> bool:
        return self._planner.needs_tools(message)

    async def answer(self, payload: ChatRequest, request_id: str) -> ChatResponse:
        calls = await asyncio.to_thread(self._planner.plan, payload.message, payload.user_id)
        if payload.user_id is None:
            return agent_response(request_id, payload.message, MISSING_USER, [])

        observations = [self._execute_authorized(call, payload.user_id) for call in calls]
        answer = await self._write_answer(payload.message, observations)
        response = agent_response(request_id, payload.message, answer, observations)
        writer = self._answer_writer
        if writer is not None:
            response.model = getattr(writer, "model_id", response.model)
            usage = getattr(writer, "last_usage", None)
            if usage:
                response.input_tokens, response.output_tokens = usage
        return response

    async def _write_answer(self, question: str, observations: list[ToolObservation]) -> str:
        writer = self._answer_writer
        if writer is None:
            return compose_answer(observations)
        text = await asyncio.to_thread(writer.write, question, observations)
        return text or compose_answer(observations)

    def _execute_authorized(self, call: ToolCall, user_id: str) -> ToolObservation:
        denied = authorize_tool(call.name, user_id, self._writers)
        if denied:
            return ToolObservation(
                name=call.name,
                arguments=call.arguments,
                result={"error": denied},
            )
        return self._registry.execute(call)
