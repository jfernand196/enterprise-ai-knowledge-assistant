from pydantic import BaseModel, Field

from app.domain.models import Mode


class EvaluationCase(BaseModel):
    id: str
    question: str
    user_id: str | None = None
    expected_mode: Mode
    expected_document: str | None = None
    expected_tools: list[str] = Field(default_factory=list)
    expected_phrases: list[str] = Field(default_factory=list)
    forbidden_phrases: list[str] = Field(default_factory=list)


class EvaluationCaseResult(BaseModel):
    id: str
    question: str
    user_id: str | None
    expected_mode: Mode
    mode: str
    passed: bool
    checks: dict[str, bool]
    retrieved_documents: list[str]
    tool_calls: list[str]
    answer: str
    model: str
    latency_ms: int
    input_tokens: int
    output_tokens: int


class EvaluationSummary(BaseModel):
    run_id: str
    created_at: str
    prompt_version: str
    cases: int
    passed: int
    pass_rate: float
    retrieval_hit_rate: float
    generation_hit_rate: float
    check_rates: dict[str, float]
    avg_latency_ms: float
    input_tokens: int
    output_tokens: int


class EvaluationReport(EvaluationSummary):
    results: list[EvaluationCaseResult]
