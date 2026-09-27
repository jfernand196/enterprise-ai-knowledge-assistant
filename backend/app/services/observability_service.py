from app.llmops.tracing import TraceRecord, TraceStore
from app.schemas.observability import MetricsResponse, TraceResponse


class ObservabilityService:
    def __init__(self, traces: TraceStore) -> None:
        self._traces = traces

    def list_traces(self) -> list[TraceResponse]:
        return [self._to_response(record) for record in self._traces.list_recent()]

    def get_trace(self, request_id: str) -> TraceResponse | None:
        record = self._traces.get(request_id)
        if record is None:
            return None
        return self._to_response(record)

    def get_metrics(self) -> MetricsResponse:
        return MetricsResponse.model_validate(self._traces.metrics())

    def _to_response(self, record: TraceRecord) -> TraceResponse:
        return TraceResponse(
            request_id=record.request_id,
            user_id=record.user_id,
            model=record.model,
            prompt_version=record.prompt_version,
            mode=record.mode,
            latency_ms=record.latency_ms,
            input_tokens=record.input_tokens,
            output_tokens=record.output_tokens,
            cost_usd=record.cost_usd,
            retrieved_documents=record.retrieved_documents,
            tool_calls=record.tool_calls,
            blocked=record.blocked,
            blocked_reason=record.blocked_reason,
        )
