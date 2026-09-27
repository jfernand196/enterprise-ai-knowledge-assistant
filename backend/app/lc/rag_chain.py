from typing import Any

from langchain_core.documents import Document
from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.retrievers import BaseRetriever
from langchain_core.runnables import (
    Runnable,
    RunnableBranch,
    RunnableLambda,
    RunnableParallel,
    RunnablePassthrough,
)

from app.rag.gemini import SYSTEM_PROMPT
from app.rag.generator import NO_CONTEXT_ANSWER

RAG_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        ("human", "Question: {question}\n\nExcerpts:\n\n{context}"),
    ]
)


def build_rag_chain(retriever: BaseRetriever, model: Runnable) -> Runnable:
    """question -> {question, documents, context, message}

    1. RunnableParallel runs the retriever and keeps the question.
    2. assign adds the formatted context.
    3. RunnableBranch skips the model when nothing was retrieved.
    4. The prompt fills the template and the model returns an AIMessage,
       which carries the text, the model name, and the token usage.
    """
    answer = RunnablePassthrough.assign(message=RAG_PROMPT | model)
    no_context = RunnablePassthrough.assign(message=RunnableLambda(lambda _: AIMessage(content=NO_CONTEXT_ANSWER)))
    return (
        RunnableParallel(documents=retriever, question=RunnablePassthrough())
        | RunnablePassthrough.assign(context=lambda state: format_documents(state["documents"]))
        | RunnableBranch((_has_no_documents, no_context), answer)
    )


def format_documents(documents: list[Document]) -> str:
    return "\n\n".join(
        f"Title: {document.metadata['title']}\n"
        f"Category: {document.metadata['category']}\n"
        f"Excerpt: {document.page_content}"
        for document in documents
    )


def _has_no_documents(state: dict[str, Any]) -> bool:
    return not state["documents"]
