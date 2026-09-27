from app.agent.answers import DEFAULT_ANSWER, compose_answer
from app.agent.tools import ToolObservation
from app.core.text import truncate_excerpt


def test_compose_answer_uses_registered_formatters() -> None:
    observations = [
        ToolObservation("get_employee_profile", {}, {"name": "Ana", "department": "People"}),
        ToolObservation("get_vacation_balance", {}, {"vacation_balance": 12}),
        ToolObservation(
            "create_hr_request",
            {},
            {"request_id": "req-1", "status": "submitted"},
        ),
    ]

    answer = compose_answer(observations)

    assert "Ana works in People." in answer
    assert "12 vacation days left" in answer
    assert "HR request req-1 was submitted." in answer


def test_compose_answer_ignores_unknown_tools() -> None:
    observations = [
        ToolObservation("future_tool", {}, {"value": "ignored"}),
        ToolObservation("get_vacation_balance", {}, {"vacation_balance": 3}),
    ]

    assert compose_answer(observations) == "You have 3 vacation days left."


def test_compose_answer_prefers_tool_errors() -> None:
    observations = [
        ToolObservation("create_hr_request", {}, {"error": "User emp-1 is not allowed"}),
    ]

    assert compose_answer(observations) == "User emp-1 is not allowed"


def test_compose_answer_defaults_when_empty() -> None:
    assert compose_answer([]) == DEFAULT_ANSWER


def test_truncate_excerpt_adds_ellipsis() -> None:
    assert truncate_excerpt("short") == "short"
    assert truncate_excerpt("a" * 181).endswith("...")
    assert len(truncate_excerpt("a" * 181)) == 180
