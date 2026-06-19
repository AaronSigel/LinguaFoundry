"""Runtime configuration for the Telegram bot service."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-backed settings for the bot adapter."""

    telegram_bot_token: str = ""
    api_base_url: str = "http://localhost:8000"
    telegram_poll_timeout: int = 30

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached bot settings."""

    return Settings()
