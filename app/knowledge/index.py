from pathlib import Path

from app.domain.models import Document
from app.knowledge.loader import load_documents
from app.rag.chunker import split_into_chunks
from app.rag.embeddings import EmbeddingPort, TfidfEmbeddingClient
from app.rag.generator import GroundedGenerator, LlmPort
from app.rag.retriever import Retriever
from app.rag.vector_store import InMemoryVectorStore


class KnowledgeIndex:
    def __init__(self, retriever: Retriever, generator: LlmPort) -> None:
        self.retriever = retriever
        self.generator = generator


def build_knowledge_index(
    documents_dir: Path,
    chunk_size: int,
    overlap: int,
    top_k: int,
    candidate_k: int = 10,
    embedder: EmbeddingPort | None = None,
    generator: LlmPort | None = None,
    documents: list[Document] | None = None,
) -> KnowledgeIndex:
    loaded = documents if documents is not None else load_documents(documents_dir)
    chunks = [
        chunk
        for document in loaded
        for chunk in split_into_chunks(document, chunk_size, overlap)
    ]
    embedder = embedder or TfidfEmbeddingClient()
    embedder.fit([chunk.text for chunk in chunks])

    store = InMemoryVectorStore()
    for chunk in chunks:
        store.upsert(chunk, embedder.embed(chunk.text))

    return KnowledgeIndex(
        retriever=Retriever(
            embedder,
            store,
            top_k=top_k,
            candidate_k=candidate_k,
        ),
        generator=generator or GroundedGenerator(),
    )
