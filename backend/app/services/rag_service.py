import asyncio

from app.core.text import truncate_excerpt
from app.domain.models import Mode, ScoredChunk
from app.knowledge.index import KnowledgeIndex
from app.schemas.chat import ChatRequest, ChatResponse, Citation


class RagService:
    def __init__(self, index: KnowledgeIndex) -> None:
        self._index = index

    async def answer(self, payload: ChatRequest, request_id: str) -> ChatResponse:
        chunks = self._index.retriever.retrieve(
            payload.message,
            category=payload.category,
            top_k=payload.top_k,
        )
        relevant = [item for item in chunks if item.score > 0]
        answer = await asyncio.to_thread(self._index.generator.generate, payload.message, relevant)
        response = ChatResponse.create(
            request_id=request_id,
            message=payload.message,
            answer=answer,
            sources=list(dict.fromkeys(item.chunk.title for item in relevant)),
            citations=[_to_citation(item) for item in relevant],
            mode=Mode.RAG,
        )
        response.model = getattr(self._index.generator, "model_id", response.model)
        usage = getattr(self._index.generator, "last_usage", None)
        if usage:
            response.input_tokens, response.output_tokens = usage
        return response


def _to_citation(item: ScoredChunk) -> Citation:
    return Citation(
        title=item.chunk.title,
        doc_id=item.chunk.doc_id,
        category=item.chunk.category,
        score=round(item.score, 4),
        excerpt=truncate_excerpt(item.chunk.text),
    )
