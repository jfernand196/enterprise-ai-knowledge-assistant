from fastapi.testclient import TestClient

from app.domain.models import Mode
from app.schemas.evaluation import EvaluationCase
from app.services.evaluation_service import Outcome, run_checks


def test_run_checks_only_scores_what_the_case_declares() -> None:
    case = EvaluationCase(id="c", question="q", expected_mode=Mode.BLOCKED)

    assert run_checks(case, Outcome.blocked("Prompt injection detected")) == {"route": True}


def test_forbidden_phrase_fails_even_when_route_and_tools_pass() -> None:
    case = EvaluationCase(
        id="c",
        question="q",
        expected_mode=Mode.AGENT,
        expected_tools=["create_hr_request"],
        forbidden_phrases=["not allowed"],
    )
    outcome = Outcome(mode=Mode.AGENT, answer="You are not allowed.", tools=["create_hr_request"])

    assert run_checks(case, outcome) == {"route": True, "tools": True, "forbidden": False}


def test_evaluation_covers_rag_agent_authorization_and_guardrails(client: TestClient) -> None:
    response = client.post("/evaluations")

    assert response.status_code == 200
    body = response.json()
    results = {item["id"]: item for item in body["results"]}
    assert body["cases"] == 7
    assert body["retrieval_hit_rate"] == 1.0
    assert results["guardrail-injection"]["mode"] == "blocked"
    assert results["authz-request-juan"]["checks"]["generation"] is True
    assert results["agent-request-ana"]["checks"]["forbidden"] is True
    assert body["pass_rate"] == 1.0, [item["id"] for item in body["results"] if not item["passed"]]


def test_evaluation_does_not_write_chat_traces(client: TestClient) -> None:
    before = client.get("/metrics").json()["requests"]

    client.post("/evaluations")

    assert client.get("/metrics").json()["requests"] == before
