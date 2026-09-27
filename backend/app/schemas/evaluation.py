from pydantic import BaseModel


class EvaluationCaseResult(BaseModel):
    question: str
    expected_document: str
    retrieved_documents: list[str]
    retrieval_hit: bool
    generation_hit: bool
    answer: str


class EvaluationReport(BaseModel):
    cases: int
    retrieval_hit_rate: float
    generation_hit_rate: float
    results: list[EvaluationCaseResult]
