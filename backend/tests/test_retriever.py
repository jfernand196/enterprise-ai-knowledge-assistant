from app.core.config import PROJECT_ROOT
from app.knowledge.index import build_knowledge_index
from app.rag.generator import NO_CONTEXT_ANSWER


def test_retriever_ranks_vacation_policy_first() -> None:
    documents_dir = PROJECT_ROOT / "data" / "documents"
    index = build_knowledge_index(
        documents_dir=documents_dir,
        chunk_size=500,
        overlap=100,
        top_k=3,
    )

    results = index.retriever.retrieve("How many vacation days do employees receive?")

    assert results
    assert results[0].chunk.title == "Vacation Policy"
    assert results[0].score > 0


def test_generator_refuses_empty_context() -> None:
    documents_dir = PROJECT_ROOT / "data" / "documents"
    index = build_knowledge_index(
        documents_dir=documents_dir,
        chunk_size=500,
        overlap=100,
        top_k=3,
    )

    assert index.generator.generate("anything", []) == NO_CONTEXT_ANSWER
