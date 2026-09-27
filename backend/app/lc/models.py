from collections.abc import Sequence
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.runnables import Runnable
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq

from app.rag.gemini import model_chain

TEMPERATURE = 0.2


def build_chat_models(
    gemini_api_key: str,
    model_id: str,
    groq_api_key: str,
    groq_model_id: str,
) -> list[BaseChatModel]:
    """Same order as the native generator: the Flash ladder, then Groq."""
    models: list[BaseChatModel] = []
    if gemini_api_key.strip():
        models.extend(_gemini(name, gemini_api_key) for name in model_chain(model_id))
    if groq_api_key.strip():
        models.append(
            ChatGroq(
                model=groq_model_id,
                api_key=groq_api_key,
                temperature=TEMPERATURE,
                max_retries=0,
            )
        )
    return models


def with_fallbacks(models: Sequence[BaseChatModel], tools: Sequence[Any] | None = None) -> Runnable:
    """Try each model in order. A 429 or timeout on one moves to the next.

    Tools must be bound to every model before chaining; binding after
    with_fallbacks would only reach the first one.
    """
    runnables = [model.bind_tools(tools) if tools else model for model in models]
    primary, *rest = runnables
    return primary.with_fallbacks(rest) if rest else primary


def model_name(message: AIMessage) -> str:
    metadata = message.response_metadata or {}
    return str(metadata.get("model_name") or metadata.get("model") or "langchain")


def token_usage(message: AIMessage) -> tuple[int, int]:
    usage = message.usage_metadata or {}
    return int(usage.get("input_tokens", 0)), int(usage.get("output_tokens", 0))


def _gemini(name: str, api_key: str) -> ChatGoogleGenerativeAI:
    options: dict[str, Any] = {}
    if "lite" not in name.lower() and "gemini-3." in name.lower():
        options["reasoning_effort"] = "minimal"
    return ChatGoogleGenerativeAI(
        model=name,
        google_api_key=api_key,
        temperature=TEMPERATURE,
        max_retries=0,
        **options,
    )
