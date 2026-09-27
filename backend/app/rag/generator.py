from typing import Protocol

from app.domain.models import ScoredChunk

NO_CONTEXT_ANSWER = (
    "I don't have enough information in the company knowledge base to answer that."
)


class LlmPort(Protocol):
    def generate(self, question: str, chunks: list[ScoredChunk]) -> str: ...


class GroundedGenerator:
    """Extractive generator that stays faithful to retrieved chunks."""

    model_id = "grounded-extractive-v1"
    last_usage: tuple[int, int] | None = None

    def generate(self, question: str, chunks: list[ScoredChunk]) -> str:
        del question
        if not chunks:
            return NO_CONTEXT_ANSWER

        parts = [
            f"According to {item.chunk.title}: {item.chunk.text}" for item in chunks
        ]
        return " ".join(parts)
