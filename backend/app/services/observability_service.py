from dataclasses import asdict

from app.llmops.tracing import TraceRecord, TraceStore
from app.schemas.observability import FeedbackRequest, MetricsResponse, TraceResponse


class ObservabilityService:
    def __init__(self, traces: TraceStore) -> None:
        self._traces = traces

    def list_traces(self, limit: int = 50) -> list[TraceResponse]:
        return [self._to_response(record) for record in self._traces.list_recent(limit)]

    def get_trace(self, request_id: str) -> TraceResponse | None:
        record = self._traces.get(request_id)
        if record is None:
            return None
        return self._to_response(record)

    def get_metrics(self) -> MetricsResponse:
        return MetricsResponse.model_validate(self._traces.metrics())

    def add_feedback(self, feedback: FeedbackRequest) -> bool:
        return self._traces.add_feedback(feedback.request_id, feedback.rating, feedback.comment)

    def _to_response(self, record: TraceRecord) -> TraceResponse:
        return TraceResponse.model_validate(asdict(record))
