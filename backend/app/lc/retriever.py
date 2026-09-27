from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from pydantic import ConfigDict

from app.rag.retriever import Retriever


class IndexRetriever(BaseRetriever):
    """Exposes the existing TF-IDF + rerank retriever as a LangChain retriever.

    Anything that accepts a BaseRetriever (chains, tools, evaluators) can use
    the same index the native RAG path uses.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    retriever: Retriever
    category: str | None = None
    top_k: int | None = None

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun,
    ) -> list[Document]:
        return [
            Document(
                page_content=item.chunk.text,
                metadata={
                    "title": item.chunk.title,
                    "doc_id": item.chunk.doc_id,
                    "category": item.chunk.category,
                    "score": round(item.score, 4),
                },
            )
            for item in self.retriever.retrieve(query, category=self.category, top_k=self.top_k)
            if item.score > 0
        ]
