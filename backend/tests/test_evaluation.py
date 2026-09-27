from fastapi.testclient import TestClient


def test_create_evaluation_hits_expected_documents(client: TestClient) -> None:
    response = client.post("/evaluations")

    assert response.status_code == 200
    body = response.json()
    assert body["cases"] == 3
    assert body["retrieval_hit_rate"] == 1.0
    assert body["generation_hit_rate"] == 1.0
