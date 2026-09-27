from app.domain.models import Chunk, ScoredChunk
from app.rag.reranker import LexicalReranker


def test_lexical_reranker_promotes_term_overlap() -> None:
    vacation = ScoredChunk(
        chunk=Chunk(
            chunk_id="v-0",
            doc_id="vacation_policy",
            title="Vacation Policy",
            category="hr",
            text="Employees receive 15 paid vacation days during the first year.",
        ),
        score=0.2,
    )
    unrelated = ScoredChunk(
        chunk=Chunk(
            chunk_id="p-0",
            doc_id="product_overview",
            title="Product Overview",
            category="product",
            text="The assistant cites source documents after retrieval.",
        ),
        score=0.9,
    )

    ranked = LexicalReranker().rerank(
        "How many vacation days do employees receive?",
        [unrelated, vacation],
        top_k=1,
    )

    assert ranked[0].chunk.title == "Vacation Policy"
