from fastapi.testclient import TestClient

from customer_support_agent.core.settings import Settings
from customer_support_agent.main import create_app


def test_live_returns_ok():
    settings = Settings(jwt_secret="testsecret", _env_file=None)
    app = create_app(settings=settings)
    client = TestClient(app)
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
