from app.domain.models import ScoredChunk
from app.rag.embeddings import EmbeddingPort
from app.rag.reranker import LexicalReranker, RerankerPort
from app.rag.vector_store import InMemoryVectorStore


class Retriever:
    def __init__(
        self,
        embedder: EmbeddingPort,
        store: InMemoryVectorStore,
        top_k: int,
        candidate_k: int,
        reranker: RerankerPort | None = None,
    ) -> None:
        self._embedder = embedder
        self._store = store
        self._top_k = top_k
        self._candidate_k = candidate_k
        self._reranker = reranker or LexicalReranker()

    def retrieve(
        self,
        query: str,
        category: str | None = None,
        top_k: int | None = None,
    ) -> list[ScoredChunk]:
        final_k = top_k or self._top_k
        query_embedding = self._embedder.embed(query)
        candidates = self._store.search(
            query_embedding,
            top_k=max(self._candidate_k, final_k),
            category=category,
        )
        return self._reranker.rerank(query, candidates, final_k)
