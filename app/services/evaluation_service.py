import json
from pathlib import Path

from app.schemas.chat import ChatRequest
from app.schemas.evaluation import EvaluationCaseResult, EvaluationReport
from app.services.rag_service import RagService


class EvaluationService:
    def __init__(self, rag_service: RagService, eval_path: Path) -> None:
        self._rag_service = rag_service
        self._eval_path = eval_path

    async def create_report(self) -> EvaluationReport:
        cases = json.loads(self._eval_path.read_text(encoding="utf-8"))
        results: list[EvaluationCaseResult] = []
        for case in cases:
            response = await self._rag_service.answer(
                ChatRequest(message=case["question"]),
                request_id="eval",
            )
            retrieval_hit = case["expected_document"] in response.sources
            generation_hit = all(
                phrase.lower() in response.answer.lower()
                for phrase in case["expected_phrases"]
            )
            results.append(
                EvaluationCaseResult(
                    question=case["question"],
                    expected_document=case["expected_document"],
                    retrieved_documents=response.sources,
                    retrieval_hit=retrieval_hit,
                    generation_hit=generation_hit,
                    answer=response.answer,
                )
            )
        total = len(results) or 1
        return EvaluationReport(
            cases=len(results),
            retrieval_hit_rate=sum(item.retrieval_hit for item in results) / total,
            generation_hit_rate=sum(item.generation_hit for item in results) / total,
            results=results,
        )
