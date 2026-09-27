from typing import Protocol

from app.domain.models import ScoredChunk
from app.rag.embeddings import tokenize


class RerankerPort(Protocol):
    def rerank(
        self,
        query: str,
        candidates: list[ScoredChunk],
        top_k: int,
    ) -> list[ScoredChunk]: ...


class LexicalReranker:
    """Reorders vector-search candidates using query-term overlap.

    Vector search casts a wide net. The reranker keeps the chunks that
    actually mention the question terms before they go to the generator.
    """

    def rerank(
        self,
        query: str,
        candidates: list[ScoredChunk],
        top_k: int,
    ) -> list[ScoredChunk]:
        query_tokens = set(tokenize(query))
        rescored = [
            ScoredChunk(
                chunk=item.chunk,
                score=_combined_score(query_tokens, item),
            )
            for item in candidates
        ]
        rescored.sort(key=lambda item: item.score, reverse=True)
        return rescored[:top_k]


def _combined_score(query_tokens: set[str], item: ScoredChunk) -> float:
    chunk_tokens = set(tokenize(item.chunk.text))
    overlap = len(query_tokens & chunk_tokens) / max(len(query_tokens), 1)
    return (0.3 * item.score) + (0.7 * overlap)
