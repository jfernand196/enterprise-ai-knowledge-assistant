from fastapi.testclient import TestClient


def test_get_health_returns_ok(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "Enterprise AI Knowledge Assistant"
    assert body["version"] == "0.7.0"
