import json
from dataclasses import dataclass, field

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool

from app.agent.tools import ToolObservation
from app.lc.models import model_name, token_usage

MAX_STEPS = 4
AGENT_PROMPT = (
    "You are an HR assistant. Use the tools to answer questions about the caller. "
    "If they ask how many vacation days they have, call get_employee_profile and get_vacation_balance. "
    "Call create_hr_request only when they ask to submit a request. "
    "Answer in one or two short sentences using only the tool results. "
    "Use the name and the exact vacation_balance if present. "
    "If a tool result has an error, include that error and do not say the request succeeded."
)


@dataclass
class AgentRun:
    answer: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    messages: list[BaseMessage] = field(default_factory=list)


async def run_tool_agent(model: Runnable, tools: list[BaseTool], question: str) -> AgentRun:
    """The tool-calling loop, written out so every step is visible.

    model must already have the tools bound (see with_fallbacks).
    Each turn the model either returns tool_calls or a final answer.
    Tool results go back as ToolMessage with the matching tool_call_id.
    """
    by_name = {tool.name: tool for tool in tools}
    messages: list[BaseMessage] = [SystemMessage(AGENT_PROMPT), HumanMessage(question)]
    run = AgentRun(answer="", model="langchain", messages=messages)
    for _ in range(MAX_STEPS):
        reply: AIMessage = await model.ainvoke(messages)
        messages.append(reply)
        _add_usage(run, reply)
        if not reply.tool_calls:
            run.answer = reply.text.strip()
            return run
        for call in reply.tool_calls:
            tool = by_name.get(call["name"])
            result = tool.invoke(call["args"]) if tool else {"error": f"Unknown tool: {call['name']}"}
            messages.append(ToolMessage(content=json.dumps(result), tool_call_id=call["id"]))
    return run


def keep_errors(answer: str, observations: list[ToolObservation]) -> str:
    for item in observations:
        error = item.result.get("error")
        if error and str(error) not in answer:
            answer = f"{error} {answer}"
    return answer.strip()


def _add_usage(run: AgentRun, reply: AIMessage) -> None:
    input_tokens, output_tokens = token_usage(reply)
    run.input_tokens += input_tokens
    run.output_tokens += output_tokens
    run.model = model_name(reply)
