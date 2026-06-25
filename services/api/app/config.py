"""Runtime configuration for the API service."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-backed settings shared by API modules."""

    app_env: str = "development"
    log_level: str = "INFO"
    service_name: str = "linguafoundry-api"
    database_url: str = "postgresql+asyncpg://localhost:5432/linguafoundry"
    database_echo: bool = False
    api_key: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached settings for dependency injection."""

    return Settings()
