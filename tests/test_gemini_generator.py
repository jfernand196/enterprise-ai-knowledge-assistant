from app.domain.models import Chunk, ScoredChunk
from app.rag.gemini import GeminiGroundedGenerator


def _chunk() -> ScoredChunk:
    return ScoredChunk(
        chunk=Chunk(
            chunk_id="vacation_policy-0",
            doc_id="vacation_policy",
            title="Vacation Policy",
            category="hr",
            text="Employees receive 15 paid vacation days during their first year.",
        ),
        score=1.0,
    )


def test_gemini_falls_through_quota_to_the_next_flash_model() -> None:
    calls: list[str] = []

    def poster(url: str, headers: dict, payload: dict) -> tuple[int, dict]:
        calls.append(payload["model"])
        if payload["model"] == "gemini-3.6-flash":
            return 429, {"error": {"message": "quota exceeded"}}
        return 200, {
            "output_text": "Employees receive 15 paid vacation days in the first year.",
            "usage": {"prompt_tokens": 20, "completion_tokens": 9},
        }

    generator = GeminiGroundedGenerator(
        gemini_api_key="test-key",
        model_id="gemini-3.6-flash",
        poster=poster,
    )

    answer = generator.generate("What is the vacation policy?", [_chunk()])

    assert "15 paid vacation days" in answer
    assert generator.model_id == "gemini-3.5-flash"
    assert calls == ["gemini-3.6-flash", "gemini-3.5-flash"]
    assert generator.last_usage == (20, 9)
