import json
from dataclasses import dataclass, field
from pathlib import Path
from time import perf_counter
from typing import Protocol
from uuid import uuid4

from app.domain.models import Mode
from app.llmops.guardrails import GuardrailRejectedError
from app.llmops.jsonl import append_jsonl, read_jsonl
from app.llmops.tracing import utc_now
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.evaluation import EvaluationCase, EvaluationCaseResult, EvaluationReport, EvaluationSummary

EVAL_REQUEST_ID = "eval"


class AnswerPort(Protocol):
    @property
    def prompt_version(self) -> str: ...

    async def run(self, payload: ChatRequest, request_id: str) -> ChatResponse: ...


@dataclass(frozen=True)
class Outcome:
    """What the assistant did for one case, whether it answered or was blocked."""

    mode: str
    answer: str
    model: str = ""
    documents: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0

    @classmethod
    def from_response(cls, response: ChatResponse) -> "Outcome":
        return cls(
            mode=response.mode,
            answer=response.answer,
            model=response.model,
            documents=response.sources,
            tools=[call.name for call in response.tool_calls],
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
        )

    @classmethod
    def blocked(cls, reason: str) -> "Outcome":
        return cls(mode=Mode.BLOCKED, answer=reason)


class EvaluationService:
    """Runs the golden set through the same path as /chat and keeps a history of runs.

    Each case checks only what it declares: route, retrieved document, tools,
    phrases that must appear, and phrases that must not.
    """

    def __init__(self, chat: AnswerPort, eval_path: Path, history_path: Path | None = None) -> None:
        self._chat = chat
        self._eval_path = eval_path
        self._history_path = history_path

    async def create_report(self) -> EvaluationReport:
        results = [await self._run_case(case) for case in self._load_cases()]
        report = build_report(results, self._chat.prompt_version)
        self._save(report)
        return report

    def history(self, limit: int = 20) -> list[EvaluationSummary]:
        if self._history_path is None:
            return []
        runs = [EvaluationSummary.model_validate(event) for event in read_jsonl(self._history_path)]
        return list(reversed(runs[-limit:]))

    def _load_cases(self) -> list[EvaluationCase]:
        raw = json.loads(self._eval_path.read_text(encoding="utf-8"))
        return [EvaluationCase.model_validate(item) for item in raw]

    async def _run_case(self, case: EvaluationCase) -> EvaluationCaseResult:
        started = perf_counter()
        payload = ChatRequest(message=case.question, user_id=case.user_id)
        try:
            outcome = Outcome.from_response(await self._chat.run(payload, EVAL_REQUEST_ID))
        except GuardrailRejectedError as exc:
            outcome = Outcome.blocked(exc.reason)
        return score_case(case, outcome, latency_ms=int((perf_counter() - started) * 1000))

    def _save(self, report: EvaluationReport) -> None:
        if self._history_path is not None:
            append_jsonl(self._history_path, report.model_dump(mode="json", exclude={"results"}))


def score_case(case: EvaluationCase, outcome: Outcome, latency_ms: int) -> EvaluationCaseResult:
    checks = run_checks(case, outcome)
    return EvaluationCaseResult(
        id=case.id,
        question=case.question,
        user_id=case.user_id,
        expected_mode=case.expected_mode,
        mode=outcome.mode,
        passed=all(checks.values()),
        checks=checks,
        retrieved_documents=outcome.documents,
        tool_calls=outcome.tools,
        answer=outcome.answer,
        model=outcome.model,
        latency_ms=latency_ms,
        input_tokens=outcome.input_tokens,
        output_tokens=outcome.output_tokens,
    )


def run_checks(case: EvaluationCase, outcome: Outcome) -> dict[str, bool]:
    text = outcome.answer.lower()
    checks = {"route": outcome.mode == case.expected_mode}
    if case.expected_document:
        checks["retrieval"] = case.expected_document in outcome.documents
    if case.expected_tools:
        checks["tools"] = set(case.expected_tools) <= set(outcome.tools)
    if case.expected_phrases:
        checks["generation"] = all(phrase.lower() in text for phrase in case.expected_phrases)
    if case.forbidden_phrases:
        checks["forbidden"] = not any(phrase.lower() in text for phrase in case.forbidden_phrases)
    return checks


def build_report(results: list[EvaluationCaseResult], prompt_version: str) -> EvaluationReport:
    total = len(results) or 1
    passed = sum(item.passed for item in results)
    names = sorted({name for item in results for name in item.checks})
    check_rates = {name: _check_rate(results, name) for name in names}
    return EvaluationReport(
        run_id=str(uuid4()),
        created_at=utc_now(),
        prompt_version=prompt_version,
        cases=len(results),
        passed=passed,
        pass_rate=round(passed / total, 4),
        retrieval_hit_rate=check_rates.get("retrieval", 0.0),
        generation_hit_rate=check_rates.get("generation", 0.0),
        check_rates=check_rates,
        avg_latency_ms=round(sum(item.latency_ms for item in results) / total, 2),
        input_tokens=sum(item.input_tokens for item in results),
        output_tokens=sum(item.output_tokens for item in results),
        results=results,
    )


def _check_rate(results: list[EvaluationCaseResult], name: str) -> float:
    applicable = [item.checks[name] for item in results if name in item.checks]
    return round(sum(applicable) / len(applicable), 4) if applicable else 0.0
