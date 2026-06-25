"""Entrypoint wiring for the Telegram bot service."""

import logging
import time

from services.bot.app.adapter import TelegramBotAdapter
from services.bot.app.api_client import ApiClient, ApiClientError
from services.bot.app.config import Settings, get_settings
from services.bot.app.telegram import TelegramClient
from services.api.app.logging import configure_logging

logger = logging.getLogger(__name__)


def create_bot(settings: Settings | None = None) -> TelegramBotAdapter:
    """Create the Telegram bot adapter with configured dependencies."""

    resolved_settings = settings or get_settings()
    return TelegramBotAdapter(
        telegram_client=TelegramClient(resolved_settings.telegram_bot_token),
        api_client=ApiClient(
            resolved_settings.api_base_url,
            api_key=resolved_settings.api_key,
        ),
    )


def wait_for_api(settings: Settings) -> None:
    """Wait until the backend API health endpoint is reachable."""

    deadline = time.monotonic() + settings.api_ready_timeout_seconds
    client = ApiClient(settings.api_base_url, api_key=settings.api_key)
    while True:
        try:
            client.health()
        except ApiClientError as exc:
            if time.monotonic() >= deadline:
                raise RuntimeError("API readiness check timed out") from exc
            logger.info("waiting for API readiness")
            time.sleep(settings.api_ready_interval_seconds)
        else:
            logger.info("API readiness check passed")
            return


def main() -> None:
    """Run the bot using Telegram long polling."""

    settings = get_settings()
    configure_logging(settings.log_level)
    wait_for_api(settings)
    create_bot(settings).run_polling(timeout=settings.telegram_poll_timeout)


if __name__ == "__main__":
    main()
