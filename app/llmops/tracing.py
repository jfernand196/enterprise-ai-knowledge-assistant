from dataclasses import dataclass, field
from typing import Any


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
    extra: dict[str, Any] = field(default_factory=dict)


class TraceStore:
    def __init__(self) -> None:
        self._records: list[TraceRecord] = []

    def add(self, record: TraceRecord) -> None:
        self._records.append(record)

    def list_recent(self, limit: int = 50) -> list[TraceRecord]:
        return list(reversed(self._records[-limit:]))

    def get(self, request_id: str) -> TraceRecord | None:
        for record in reversed(self._records):
            if record.request_id == request_id:
                return record
        return None

    def metrics(self) -> dict[str, float | int]:
        total = len(self._records)
        if total == 0:
            return {
                "requests": 0,
                "blocked": 0,
                "error_rate": 0.0,
                "avg_latency_ms": 0.0,
                "p95_latency_ms": 0.0,
                "input_tokens": 0,
                "output_tokens": 0,
                "cost_usd": 0.0,
                "rag_requests": 0,
                "agent_requests": 0,
            }
        latencies = sorted(record.latency_ms for record in self._records)
        blocked = sum(record.blocked for record in self._records)
        p95_index = min(len(latencies) - 1, max(0, int(len(latencies) * 0.95) - 1))
        return {
            "requests": total,
            "blocked": blocked,
            "error_rate": round(blocked / total, 4),
            "avg_latency_ms": round(sum(latencies) / total, 2),
            "p95_latency_ms": latencies[p95_index],
            "input_tokens": sum(record.input_tokens for record in self._records),
            "output_tokens": sum(record.output_tokens for record in self._records),
            "cost_usd": round(sum(record.cost_usd for record in self._records), 6),
            "rag_requests": sum(record.mode == "rag" for record in self._records),
            "agent_requests": sum(record.mode == "agent" for record in self._records),
        }
