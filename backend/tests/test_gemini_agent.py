import json

from app.agent.gemini_agent import GeminiAnswerWriter, GeminiPlanner
from app.agent.tools import ToolObservation
from app.rag.gemini import GeminiGroundedGenerator


def _client(payload: dict) -> GeminiGroundedGenerator:
    def poster(url: str, headers: dict, body: dict) -> tuple[int, dict]:
        del url, headers, body
        return 200, {"output_text": json.dumps(payload)}

    return GeminiGroundedGenerator(gemini_api_key="test-key", model_id="gemini-3.6-flash", poster=poster)


def test_gemini_planner_uses_the_caller_user_id() -> None:
    planner = GeminiPlanner(
        _client(
            {
                "needs_tools": True,
                "calls": [
                    {
                        "name": "get_vacation_balance",
                        "arguments": {"user_id": "emp-2"},
                    }
                ],
            }
        )
    )

    calls = planner.plan("How many vacation days do I have left?", "emp-1")

    assert planner.needs_tools("How many vacation days do I have left?") is True
    assert calls[0].name == "get_vacation_balance"
    assert calls[0].arguments["user_id"] == "emp-1"


def test_gemini_planner_leaves_policy_questions_on_rag() -> None:
    planner = GeminiPlanner(_client({"needs_tools": False}))

    assert planner.needs_tools("What is the vacation policy?") is False
    assert planner.plan("What is the vacation policy?", "emp-1") == []


def test_gemini_answer_keeps_authorization_errors() -> None:
    writer = GeminiAnswerWriter(_client({}))
    writer._client.complete = lambda system, user: "Your request was submitted."  # type: ignore[method-assign]

    answer = writer.write(
        "Please submit a time off request",
        [
            ToolObservation(
                name="create_hr_request",
                arguments={"user_id": "emp-1"},
                result={"error": "User emp-1 is not allowed to execute create_hr_request"},
            )
        ],
    )

    assert "not allowed" in answer
