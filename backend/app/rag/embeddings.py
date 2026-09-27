import math
import re
from collections import Counter
from typing import Protocol

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(text.lower())


class EmbeddingPort(Protocol):
    def fit(self, texts: list[str]) -> None: ...
    def embed(self, text: str) -> list[float]: ...


class TfidfEmbeddingClient:
    """Local TF-IDF embeddings so the RAG pipeline runs without an API key.

    Swap this for sentence-transformers or an embedding API via EmbeddingPort.
    """

    def __init__(self) -> None:
        self._idf: dict[str, float] = {}
        self._vocab: list[str] = []

    def fit(self, texts: list[str]) -> None:
        document_count = max(len(texts), 1)
        df: Counter[str] = Counter()
        for text in texts:
            df.update(set(tokenize(text)))
        self._vocab = sorted(df)
        self._idf = {
            token: math.log((document_count + 1) / (count + 1)) + 1
            for token, count in df.items()
        }

    def embed(self, text: str) -> list[float]:
        if not self._vocab:
            raise RuntimeError("TfidfEmbeddingClient.fit() must run before embed()")
        tf = Counter(tokenize(text))
        total = sum(tf.values()) or 1
        vector = [
            (tf[token] / total) * self._idf.get(token, 0.0) for token in self._vocab
        ]
        return _l2_normalize(vector)


def cosine_similarity(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=True))


def _l2_normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]
