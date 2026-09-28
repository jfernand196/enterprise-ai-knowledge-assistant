from pydantic import BaseModel, Field

from app.domain.models import EXTRACTIVE_MODEL_ID


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    user_id: str | None = None
    category: str | None = Field(
        default=None,
        description="Optional metadata filter: hr, security, product, customer",
    )
    top_k: int | None = Field(default=None, ge=1, le=10)


class Citation(BaseModel):
    title: str
    doc_id: str
    category: str
    score: float
    excerpt: str


class ToolCallResult(BaseModel):
    name: str
    arguments: dict[str, str]
    result: dict


class ChatResponse(BaseModel):
    request_id: str
    message: str
    answer: str
    sources: list[str]
    citations: list[Citation]
    tool_calls: list[ToolCallResult]
    mode: str
    model: str = EXTRACTIVE_MODEL_ID
    prompt_version: str = "v1"
    latency_ms: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0

    @classmethod
    def create(
        cls,
        *,
        request_id: str,
        message: str,
        answer: str,
        mode: str,
        sources: list[str] | None = None,
        citations: list[Citation] | None = None,
        tool_calls: list[ToolCallResult] | None = None,
    ) -> "ChatResponse":
        return cls(
            request_id=request_id,
            message=message,
            answer=answer,
            sources=sources if sources is not None else [],
            citations=citations if citations is not None else [],
            tool_calls=tool_calls if tool_calls is not None else [],
            mode=mode,
        )
