from fastapi.testclient import TestClient

from customer_support_agent.main import create_app


def test_create_app():
    app = create_app()
    client = TestClient(app)
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
