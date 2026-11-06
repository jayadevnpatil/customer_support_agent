import pytest

from customer_support_agent.core.settings import Settings


@pytest.fixture
def project_settings() -> Settings:
    return Settings(jwt_secret="super-secret", _env_file=None)
