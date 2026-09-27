from collections.abc import Callable
from typing import Any

import httpx

from app.domain.models import ScoredChunk
from app.rag.generator import NO_CONTEXT_ANSWER, GroundedGenerator

GEMINI_URLS = (
    "https://generativelanguage.googleapis.com/v1beta2/interactions",
    "https://generativelanguage.googleapis.com/v1beta/interactions",
)
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
FLASH_LADDER = (
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
)
SYSTEM_PROMPT = (
    "You answer questions about company policy using only the excerpts provided. "
    "Name the document title in the first sentence. "
    "Copy every number, deadline, and exception that answers the question, including rollover and payout. "
    "Do not replace a number with a vague phrase. "
    "If the excerpts do not contain the answer, say you do not have enough information "
    "in the company knowledge base. Do not invent policy."
)

Poster = Callable[[str, dict[str, str], dict[str, Any]], tuple[int, dict[str, Any]]]


class GeminiGroundedGenerator:
    """Answers from retrieved excerpts using the Tech Sphere Gemini Flash chain.

    If every Flash model is out of quota, it tries the Groq Llama key from that
    same project, then the extractive generator.
    """

    def __init__(
        self,
        gemini_api_key: str,
        model_id: str,
        groq_api_key: str = "",
        groq_model_id: str = "openai/gpt-oss-120b",
        poster: Poster | None = None,
    ) -> None:
        self._gemini_api_key = gemini_api_key.strip()
        self._groq_api_key = groq_api_key.strip()
        self._groq_model_id = groq_model_id
        self._models = model_chain(model_id)
        self._poster = poster or _post
        self._extractive = GroundedGenerator()
        self.model_id = self._models[0]
        self.last_usage: tuple[int, int] | None = None

    def generate(self, question: str, chunks: list[ScoredChunk]) -> str:
        if not chunks:
            self.model_id = "grounded-extractive-v1"
            self.last_usage = None
            return NO_CONTEXT_ANSWER
        text = self.complete(SYSTEM_PROMPT, _user_prompt(question, chunks))
        if text:
            return text
        self.model_id = self._extractive.model_id
        return self._extractive.generate(question, chunks)

    def complete(self, system: str, user: str) -> str:
        for model_id in self._models:
            text, usage = self._try_gemini(model_id, system, user)
            if text:
                self.model_id = model_id
                self.last_usage = _add_usage(self.last_usage, usage)
                return text
        if self._groq_api_key:
            text, usage = self._try_groq(system, user)
            if text:
                self.model_id = self._groq_model_id
                self.last_usage = _add_usage(self.last_usage, usage)
                return text
        return ""

    def _try_gemini(self, model_id: str, system: str, user: str) -> tuple[str, tuple[int, int] | None]:
        generation_config: dict[str, Any] = {"temperature": 0.2, "max_output_tokens": 1024}
        if "lite" not in model_id.lower() and "gemini-3." in model_id.lower():
            generation_config["thinking_level"] = "minimal"
            generation_config["thinking_summaries"] = "none"
        payload = {
            "model": model_id,
            "input": f"{system}\n\n---\n\n{user}",
            "store": False,
            "generation_config": generation_config,
        }
        headers = {"Content-Type": "application/json", "x-goog-api-key": self._gemini_api_key}
        for url in GEMINI_URLS:
            status, body = self._poster(url, headers, payload)
            if status == 200:
                return _gemini_text(body), _usage(body)
            if status not in {404, 405}:
                return "", None
        return "", None

    def _try_groq(self, system: str, user: str) -> tuple[str, tuple[int, int] | None]:
        payload = {
            "model": self._groq_model_id,
            "temperature": 0.2,
            "max_tokens": 1024,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        headers = {
            "Authorization": f"Bearer {self._groq_api_key}",
            "Content-Type": "application/json",
        }
        status, body = self._poster(GROQ_URL, headers, payload)
        if status != 200:
            return "", None
        text = (body.get("choices") or [{}])[0].get("message", {}).get("content") or ""
        return text.strip(), _usage(body)


def model_chain(primary: str) -> list[str]:
    key = primary.strip()
    if key in FLASH_LADDER:
        return list(FLASH_LADDER[FLASH_LADDER.index(key) :])
    rest = [model for model in FLASH_LADDER if model != key]
    return [key] + rest if key else list(FLASH_LADDER)


def build_chat_generator(
    provider: str,
    gemini_api_key: str,
    model_id: str,
    groq_api_key: str,
    groq_model_id: str,
) -> GeminiGroundedGenerator | GroundedGenerator:
    if provider.strip().lower() != "gemini" or not gemini_api_key.strip():
        return GroundedGenerator()
    return GeminiGroundedGenerator(
        gemini_api_key=gemini_api_key,
        model_id=model_id,
        groq_api_key=groq_api_key,
        groq_model_id=groq_model_id,
    )


def _user_prompt(question: str, chunks: list[ScoredChunk]) -> str:
    excerpts = [
        f"Title: {item.chunk.title}\nCategory: {item.chunk.category}\nExcerpt: {item.chunk.text}"
        for item in chunks
    ]
    return f"Question: {question}\n\nExcerpts:\n\n" + "\n\n".join(excerpts)


def _gemini_text(body: dict[str, Any]) -> str:
    direct = body.get("output_text")
    if isinstance(direct, str) and direct.strip():
        return direct.strip()
    chunks: list[str] = []
    for step in body.get("steps") or []:
        if not isinstance(step, dict):
            continue
        for part in step.get("content") or []:
            if isinstance(part, dict) and part.get("text"):
                chunks.append(str(part["text"]))
    return "".join(chunks).strip()


def _usage(body: dict[str, Any]) -> tuple[int, int] | None:
    raw = body.get("usageMetadata") or body.get("usage") or {}
    if not isinstance(raw, dict) or not raw:
        return None
    prompt = (
        raw.get("promptTokenCount")
        or raw.get("prompt_tokens")
        or raw.get("input_tokens")
        or raw.get("total_input_tokens")
    )
    completion = (
        raw.get("candidatesTokenCount")
        or raw.get("completion_tokens")
        or raw.get("output_tokens")
        or raw.get("total_output_tokens")
    )
    if prompt is None and completion is None:
        return None
    return int(prompt or 0), int(completion or 0)


def _add_usage(
    current: tuple[int, int] | None,
    added: tuple[int, int] | None,
) -> tuple[int, int] | None:
    if added is None:
        return current
    if current is None:
        return added
    return current[0] + added[0], current[1] + added[1]


def _post(url: str, headers: dict[str, str], payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    try:
        response = httpx.post(url, headers=headers, json=payload, timeout=45)
    except httpx.HTTPError:
        return 599, {}
    try:
        body = response.json()
    except ValueError:
        body = {}
    if not isinstance(body, dict):
        body = {}
    return response.status_code, body
