import asyncio
from time import perf_counter
from typing import Protocol
from uuid import uuid4

from app.llmops.guardrails import GuardrailRejectedError, check_input, check_output
from app.llmops.tracing import TraceRecord, TraceStore
from app.llmops.usage import estimate_cost_usd, estimate_tokens
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.agent_service import AgentService
from app.services.rag_service import RagService


class OrchestratorPort(Protocol):
    async def answer(self, payload: ChatRequest, request_id: str) -> ChatResponse: ...


class ChatService:
    def __init__(
        self,
        rag_service: RagService,
        agent_service: AgentService,
        traces: TraceStore,
        model: str,
        prompt_version: str,
        input_rate: float,
        output_rate: float,
        orchestrator: OrchestratorPort | None = None,
    ) -> None:
        self._rag_service = rag_service
        self._agent_service = agent_service
        self._traces = traces
        self._model = model
        self._prompt_version = prompt_version
        self._input_rate = input_rate
        self._output_rate = output_rate
        self._orchestrator = orchestrator

    async def create_reply(self, payload: ChatRequest) -> ChatResponse:
        request_id = str(uuid4())
        started = perf_counter()
        try:
            check_input(payload.message)
            response = await self._route(payload, request_id)
            response.answer = check_output(response.answer)
            return self._finalize(payload, response, started, blocked=False)
        except GuardrailRejectedError as exc:
            self.record_blocked(payload, request_id, exc.reason, started)
            raise

    async def _route(self, payload: ChatRequest, request_id: str) -> ChatResponse:
        if self._orchestrator is not None:
            return await self._orchestrator.answer(payload, request_id)
        needs_tools = await asyncio.to_thread(self._agent_service.needs_tools, payload.message)
        if needs_tools:
            return await self._agent_service.answer(payload, request_id)
        return await self._rag_service.answer(payload, request_id)

    def record_blocked(self, payload: ChatRequest, request_id: str, reason: str, started: float) -> None:
        input_tokens = estimate_tokens(payload.message)
        self._traces.add(
            TraceRecord(
                request_id=request_id,
                user_id=payload.user_id,
                model=self._model,
                prompt_version=self._prompt_version,
                mode="blocked",
                latency_ms=int((perf_counter() - started) * 1000),
                input_tokens=input_tokens,
                output_tokens=0,
                cost_usd=estimate_cost_usd(input_tokens, 0, self._input_rate, self._output_rate),
                retrieved_documents=[],
                tool_calls=[],
                blocked=True,
                blocked_reason=reason,
            )
        )

    def _finalize(
        self,
        payload: ChatRequest,
        response: ChatResponse,
        started: float,
        blocked: bool,
    ) -> ChatResponse:
        if response.input_tokens == 0 and response.output_tokens == 0:
            response.input_tokens = estimate_tokens(payload.message)
            response.output_tokens = estimate_tokens(response.answer)
        input_tokens = response.input_tokens
        output_tokens = response.output_tokens
        if response.model == "grounded-extractive-v1":
            response.model = self._model
        response.prompt_version = self._prompt_version
        response.latency_ms = int((perf_counter() - started) * 1000)
        response.input_tokens = input_tokens
        response.output_tokens = output_tokens
        response.cost_usd = estimate_cost_usd(
            input_tokens,
            output_tokens,
            self._input_rate,
            self._output_rate,
        )
        self._traces.add(
            TraceRecord(
                request_id=response.request_id,
                user_id=payload.user_id,
                model=response.model,
                prompt_version=response.prompt_version,
                mode=response.mode,
                latency_ms=response.latency_ms,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                cost_usd=response.cost_usd,
                retrieved_documents=response.sources,
                tool_calls=[item.name for item in response.tool_calls],
                blocked=blocked,
            )
        )
        return response
