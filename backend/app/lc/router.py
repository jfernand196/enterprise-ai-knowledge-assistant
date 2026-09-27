from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from app.agent.planner import KeywordPlanner

ROUTE_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Decide if an HR assistant needs employee tools. "
            "Company-wide policy questions do not. "
            "Questions about the speaker's own profile, vacation balance, or a request to submit do.",
        ),
        ("human", "{question}"),
    ]
)


class Route(BaseModel):
    needs_tools: bool = Field(description="True when the question is about the speaker or asks to submit a request.")


class StructuredRouter:
    """Routes with with_structured_output: the model returns a Route object, not text to parse.

    If every model fails, the keyword planner decides, as in the native path.
    """

    def __init__(self, models: list[BaseChatModel]) -> None:
        chains = [ROUTE_PROMPT | model.with_structured_output(Route) for model in models]
        primary, *rest = chains
        self._chain = primary.with_fallbacks(rest) if rest else primary
        self._fallback = KeywordPlanner()
        self._cache: dict[str, bool] = {}

    def needs_tools(self, message: str) -> bool:
        if message not in self._cache:
            try:
                route = self._chain.invoke({"question": message})
                self._cache[message] = bool(route.needs_tools)
            except Exception:
                return self._fallback.needs_tools(message)
        return self._cache[message]
