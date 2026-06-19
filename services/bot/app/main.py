"""Entrypoint wiring for the Telegram bot service."""

from services.bot.app.adapter import TelegramBotAdapter
from services.bot.app.api_client import ApiClient
from services.bot.app.config import Settings, get_settings
from services.bot.app.telegram import TelegramClient


def create_bot(settings: Settings | None = None) -> TelegramBotAdapter:
    """Create the Telegram bot adapter with configured dependencies."""

    resolved_settings = settings or get_settings()
    return TelegramBotAdapter(
        telegram_client=TelegramClient(resolved_settings.telegram_bot_token),
        api_client=ApiClient(resolved_settings.api_base_url),
    )


def main() -> None:
    """Run the bot using Telegram long polling."""

    settings = get_settings()
    create_bot(settings).run_polling(timeout=settings.telegram_poll_timeout)


if __name__ == "__main__":
    main()
