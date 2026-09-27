from app.domain.models import Chunk, ScoredChunk
from app.rag.embeddings import cosine_similarity


class InMemoryVectorStore:
    def __init__(self) -> None:
        self._items: list[tuple[Chunk, list[float]]] = []

    def upsert(self, chunk: Chunk, embedding: list[float]) -> None:
        self._items.append((chunk, embedding))

    def search(
        self,
        query_embedding: list[float],
        top_k: int,
        category: str | None = None,
    ) -> list[ScoredChunk]:
        scored = [
            ScoredChunk(chunk=chunk, score=cosine_similarity(query_embedding, embedding))
            for chunk, embedding in self._items
            if category is None or chunk.category == category
        ]
        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[:top_k]
