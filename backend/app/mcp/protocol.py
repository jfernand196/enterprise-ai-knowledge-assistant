from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class McpToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]


@dataclass(frozen=True)
class McpRequest:
    method: str
    params: dict[str, Any]


@dataclass(frozen=True)
class McpResponse:
    result: Any
    error: str | None = None
