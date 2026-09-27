from fastapi.testclient import TestClient


def test_create_chat_message_answers_from_vacation_policy(client: TestClient) -> None:
    response = client.post("/chat", json={"message": "What is the vacation policy?"})

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "rag"
    assert body["request_id"]
    assert "Vacation Policy" in body["sources"]
    assert "15 paid vacation days" in body["answer"]
    assert any(item["title"] == "Vacation Policy" for item in body["citations"])
    assert any(item["category"] == "hr" for item in body["citations"])


def test_create_chat_message_cites_security_policy(client: TestClient) -> None:
    response = client.post(
        "/chat",
        json={"message": "Do employees need multi-factor authentication?"},
    )

    assert response.status_code == 200
    body = response.json()
    assert "Security Policy" in body["sources"]
    assert "multi-factor authentication" in body["answer"].lower()


def test_create_chat_message_filters_by_category(client: TestClient) -> None:
    response = client.post(
        "/chat",
        json={
            "message": "What is the vacation policy?",
            "category": "security",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert "Vacation Policy" not in body["sources"]


def test_create_chat_message_rejects_empty_message(client: TestClient) -> None:
    response = client.post("/chat", json={"message": ""})

    assert response.status_code == 422
