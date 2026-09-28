from typing import Literal

from pydantic import BaseModel, Field


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
    question: str
    created_at: str
    feedback: Literal["up", "down"] | None
    feedback_comment: str | None


class UsageSummary(BaseModel):
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
    feedback_up: int
    feedback_down: int
    satisfaction: float | None


class GroupMetrics(UsageSummary):
    key: str


class MetricsResponse(UsageSummary):
    by_prompt_version: list[GroupMetrics]
    by_model: list[GroupMetrics]


class FeedbackRequest(BaseModel):
    request_id: str = Field(min_length=1, max_length=64)
    rating: Literal["up", "down"]
    comment: str | None = Field(default=None, max_length=500)
