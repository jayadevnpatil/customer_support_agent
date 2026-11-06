from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from customer_support_agent.core.exceptions import NotFoundAppError
from customer_support_agent.main import create_app


class EchoRequest(BaseModel):
    message: str = Field(min_length=1, max_length=5)


def echo(body: EchoRequest) -> dict[str, str]:
    return {"message": body.message}


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


def test_unknown_url_returns_contract_shape(project_settings):
    client = TestClient(create_app(project_settings))

    response = client.get("/no-such-url")

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "NOT_FOUND",
            "message": "Not Found",
            "retryable": False,
            "correlation_id": None,
        }
    }


def test_wrong_method_returns_contract_shape(project_settings):
    client = TestClient(create_app(project_settings))

    response = client.post("/health/live")  # the route only allows GET

    assert response.status_code == 405
    assert response.json()["error"]["code"] == "METHOD_NOT_ALLOWED"
    assert response.headers["allow"] == "GET"


def test_invalid_body_returns_validation_error(project_settings):
    app = create_app(project_settings)
    app.add_api_route("/echo", echo, methods=["POST"])
    client = TestClient(app)

    response = client.post("/echo", json={"message": "far too long"})

    assert response.status_code == 422
    assert response.json() == {
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "The request is invalid.",
            "retryable": False,
            "correlation_id": None,
            "details": [
                {
                    "field": "message",
                    "issue": "string_too_long",
                    "message": "String should have at most 5 characters",
                }
            ],
        }
    }
    assert "far too long" not in response.text  # user input is never echoed back
