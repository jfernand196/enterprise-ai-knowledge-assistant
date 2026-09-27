from pydantic import BaseModel


class TraceResponse(BaseModel):
    request_id: str
    user_id: str | None
    model: str
    prompt_version: str
    mode: str
    latency_ms: int
    input_tokens: int
    output_tokens: int
    cost_usd: float
    retrieved_documents: list[str]
    tool_calls: list[str]
    blocked: bool
    blocked_reason: str | None


class MetricsResponse(BaseModel):
    requests: int
    blocked: int
    error_rate: float
    avg_latency_ms: float
    p95_latency_ms: float
    input_tokens: int
    output_tokens: int
    cost_usd: float
    rag_requests: int
    agent_requests: int
