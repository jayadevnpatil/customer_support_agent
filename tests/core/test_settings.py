import pytest
from pydantic import ValidationError

from customer_support_agent.core.settings import Settings


def test_missing_jwt_secret_fails(monkeypatch):
    monkeypatch.delenv("JWT_SECRET", raising=False)

    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None)

    error = exc_info.value.errors()[0]
    assert error["loc"] == ("jwt_secret",)
    assert error["type"] == "missing"


def test_secret_is_masked():
    settings = Settings(jwt_secret="super-secret", _env_file=None)

    assert "super-secret" not in repr(settings)
    assert settings.jwt_secret.get_secret_value() == "super-secret"
