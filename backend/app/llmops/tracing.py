import threading
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from app.domain.models import Mode
from app.llmops.jsonl import append_jsonl, read_jsonl

Rating = Literal["up", "down"]

TRACE_EVENT = "trace"
FEEDBACK_EVENT = "feedback"
P95 = 0.95


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


@dataclass
class TraceRecord:
    request_id: str
    user_id: str | None
    model: str
    prompt_version: str
    mode: str
    latency_ms: int
    input_tokens: int
    output_tokens: int
    cost_usd: float
    retrieved_documents: list[str]
    tool_calls: list[str]
    blocked: bool = False
    blocked_reason: str | None = None
    question: str = ""
    created_at: str = field(default_factory=utc_now)
    feedback: Rating | None = None
    feedback_comment: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


class TraceStore:
    """Keeps traces in memory and, when given a path, appends them to a JSONL file.

    Feedback is appended as its own event instead of rewriting the trace line,
    so the file is append-only and survives a crash mid-write.
    """

    def __init__(self, path: Path | None = None) -> None:
        self._records: list[TraceRecord] = []
        self._by_id: dict[str, TraceRecord] = {}
        self._path = path
        self._lock = threading.Lock()
        if path is not None:
            self._replay(path)

    def add(self, record: TraceRecord) -> None:
        with self._lock:
            self._remember(record)
            self._persist({"type": TRACE_EVENT, **asdict(record)})

    def add_feedback(self, request_id: str, rating: Rating, comment: str | None) -> bool:
        with self._lock:
            record = self._by_id.get(request_id)
            if record is None:
                return False
            _apply_feedback(record, rating, comment)
            self._persist({"type": FEEDBACK_EVENT, "request_id": request_id, "rating": rating, "comment": comment})
            return True

    def list_recent(self, limit: int = 50) -> list[TraceRecord]:
        return list(reversed(self._records[-limit:]))

    def get(self, request_id: str) -> TraceRecord | None:
        return self._by_id.get(request_id)

    def metrics(self) -> dict[str, Any]:
        return {
            **summarize(self._records),
            "by_prompt_version": _grouped(self._records, lambda record: record.prompt_version),
            "by_model": _grouped(self._records, lambda record: record.model),
        }

    def _remember(self, record: TraceRecord) -> None:
        self._records.append(record)
        self._by_id[record.request_id] = record

    def _persist(self, event: dict[str, Any]) -> None:
        if self._path is not None:
            append_jsonl(self._path, event)

    def _replay(self, path: Path) -> None:
        for event in read_jsonl(path):
            kind = event.pop("type", TRACE_EVENT)
            if kind == TRACE_EVENT:
                self._remember(TraceRecord(**event))
            elif kind == FEEDBACK_EVENT and event.get("request_id") in self._by_id:
                _apply_feedback(self._by_id[event["request_id"]], event.get("rating"), event.get("comment"))


def summarize(records: list[TraceRecord]) -> dict[str, Any]:
    total = len(records)
    latencies = sorted(record.latency_ms for record in records)
    blocked = sum(record.blocked for record in records)
    up = sum(record.feedback == "up" for record in records)
    down = sum(record.feedback == "down" for record in records)
    return {
        "requests": total,
        "blocked": blocked,
        "error_rate": _ratio(blocked, total) or 0.0,
        "avg_latency_ms": round(sum(latencies) / total, 2) if total else 0.0,
        "p95_latency_ms": _percentile(latencies, P95),
        "input_tokens": sum(record.input_tokens for record in records),
        "output_tokens": sum(record.output_tokens for record in records),
        "cost_usd": round(sum(record.cost_usd for record in records), 6),
        "rag_requests": sum(record.mode == Mode.RAG for record in records),
        "agent_requests": sum(record.mode == Mode.AGENT for record in records),
        "feedback_up": up,
        "feedback_down": down,
        "satisfaction": _ratio(up, up + down),
    }


def _apply_feedback(record: TraceRecord, rating: Rating | None, comment: str | None) -> None:
    record.feedback = rating
    record.feedback_comment = comment


def _grouped(records: list[TraceRecord], key: Callable[[TraceRecord], str]) -> list[dict[str, Any]]:
    groups: dict[str, list[TraceRecord]] = {}
    for record in records:
        groups.setdefault(key(record), []).append(record)
    return [{"key": name, **summarize(items)} for name, items in sorted(groups.items())]


def _ratio(part: int, whole: int) -> float | None:
    return round(part / whole, 4) if whole else None


def _percentile(sorted_values: list[int], fraction: float) -> float:
    if not sorted_values:
        return 0.0
    index = min(len(sorted_values) - 1, max(0, int(len(sorted_values) * fraction) - 1))
    return sorted_values[index]
