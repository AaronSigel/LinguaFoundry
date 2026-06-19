"""Runtime configuration for the API service."""

from dataclasses import dataclass, field
import os


DEFAULT_DATABASE_ACCOUNT = ("linguafoundry", "linguafoundry")  # pragma: allowlist secret
DEFAULT_DATABASE_HOST = "localhost"
DEFAULT_DATABASE_PORT = 5432
DEFAULT_DATABASE_NAME = "linguafoundry"


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _default_database_url() -> str:
    username, credential = DEFAULT_DATABASE_ACCOUNT
    return (
        "postgresql+asyncpg://"
        f"{username}:{credential}"
        f"@{DEFAULT_DATABASE_HOST}:{DEFAULT_DATABASE_PORT}/{DEFAULT_DATABASE_NAME}"
    )


@dataclass(frozen=True)
class Settings:
    """Environment-backed API settings."""

    database_url: str = field(
        default_factory=lambda: os.getenv("DATABASE_URL", _default_database_url())
    )
    database_echo: bool = field(default_factory=lambda: _env_bool("DATABASE_ECHO"))


def get_settings() -> Settings:
    """Return current API settings from environment variables."""

    return Settings()
