from dataclasses import dataclass
from enum import StrEnum

EXTRACTIVE_MODEL_ID = "grounded-extractive-v1"


class Mode(StrEnum):
    RAG = "rag"
    AGENT = "agent"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class Document:
    doc_id: str
    title: str
    category: str
    content: str


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    doc_id: str
    title: str
    category: str
    text: str


@dataclass(frozen=True)
class ScoredChunk:
    chunk: Chunk
    score: float
