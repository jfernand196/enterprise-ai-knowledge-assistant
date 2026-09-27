from fastapi.testclient import TestClient

from app.agent.planner import KeywordPlanner


def test_policy_question_stays_on_rag(client: TestClient) -> None:
    response = client.post("/chat", json={"message": "What is the vacation policy?"})

    assert response.json()["mode"] == "rag"
    assert response.json()["tool_calls"] == []


def test_create_chat_message_uses_vacation_tools(client: TestClient) -> None:
    response = client.post(
        "/chat",
        json={
            "message": "How many vacation days do I have left?",
            "user_id": "emp-1",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "agent"
    assert "8 vacation days left" in body["answer"]
    assert "Juan Perez" in body["answer"]
    names = [item["name"] for item in body["tool_calls"]]
    assert names == [
        "get_employee_profile",
        "get_vacation_balance",
        "search_documents",
    ]
    assert "Vacation Policy" in body["sources"]


def test_create_chat_message_requires_user_id_for_tools(client: TestClient) -> None:
    response = client.post(
        "/chat",
        json={"message": "How many vacation days do I have left?"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "agent"
    assert "user_id" in body["answer"]
    assert body["tool_calls"] == []


def test_create_chat_message_submits_hr_request(client: TestClient) -> None:
    response = client.post(
        "/chat",
        json={
            "message": "Please submit a time off request for next Friday",
            "user_id": "emp-2",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "agent"
    assert "submitted" in body["answer"]
    assert any(item["name"] == "create_hr_request" for item in body["tool_calls"])


def test_keyword_planner_does_not_treat_policy_as_personal() -> None:
    planner = KeywordPlanner()

    assert planner.needs_tools("How many vacation days do employees receive?") is False
    assert planner.needs_tools("How many vacation days do I have left?") is True
