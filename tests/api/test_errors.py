from fastapi.testclient import TestClient

from customer_support_agent.core.exceptions import NotFoundAppError
from customer_support_agent.main import create_app


def test_app_error_returns_contract_shape(project_settings):
    def raise_not_found():
        raise NotFoundAppError()

    # Arrange: register a throwaway route that raises our error
    app = create_app(project_settings)
    app.add_api_route("/boom", raise_not_found)
    client = TestClient(app)

    # Act: send a request to it
    response = client.get("/boom")

    # Assert: our handler produced the contract shape
    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "NOT_FOUND",
            "message": "Resource not found.",
            "retryable": False,
            "correlation_id": None,
        }
    }
