"""Runtime configuration for the API service."""

from dataclasses import dataclass, field
import os


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    """Environment-backed API settings."""

    database_url: str = field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://localhost:5432/linguafoundry",
        )
    )
    database_echo: bool = field(default_factory=lambda: _env_bool("DATABASE_ECHO"))


def get_settings() -> Settings:
    """Return current API settings from environment variables."""

    return Settings()
