from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_env: Literal["local", "test", "prod"] = "local"
    jwt_secret: SecretStr
    jwt_algorithm: str = "HS256"
    max_body_bytes: int = 1024 * 16


def get_settings() -> Settings:
    return Settings()
