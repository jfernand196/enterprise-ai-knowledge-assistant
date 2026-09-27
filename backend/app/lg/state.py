import operator
from typing import Annotated, TypedDict

from langchain_core.documents import Document
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class GraphState(TypedDict):
    """Shared state every node reads and returns partial updates to.

    Fields without an annotation are overwritten by the last node that sets
    them. Annotated fields use a reducer that merges instead:
    add_messages appends to the conversation, operator.add sums tokens
    across every model call in the run.
    """

    question: str
    user_id: str | None
    category: str | None
    top_k: int | None
    route: str
    documents: list[Document]
    messages: Annotated[list[AnyMessage], add_messages]
    answer: str
    model: str
    input_tokens: Annotated[int, operator.add]
    output_tokens: Annotated[int, operator.add]
