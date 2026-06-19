from services.bot.app.adapter import TelegramBotAdapter
from services.bot.app.api_client import ApiClientError


class RecordingTelegramClient:
    def __init__(self) -> None:
        self.sent_messages: list[tuple[int, str]] = []

    def send_message(self, chat_id: int, text: str) -> None:
        self.sent_messages.append((chat_id, text))


class HealthyApiClient:
    def health(self) -> dict[str, str]:
        return {"status": "ok"}


class UnreachableApiClient:
    def health(self) -> dict[str, str]:
        raise ApiClientError("offline")


def test_start_command_sends_welcome_message() -> None:
    telegram = RecordingTelegramClient()
    bot = TelegramBotAdapter(telegram, HealthyApiClient())

    handled = bot.process_update(
        {"message": {"chat": {"id": 123}, "text": "/start"}}
    )

    assert handled is True
    assert telegram.sent_messages == [
        (123, "Welcome to LinguaFoundry. Use /help to see available commands.")
    ]


def test_help_command_lists_available_commands() -> None:
    telegram = RecordingTelegramClient()
    bot = TelegramBotAdapter(telegram, HealthyApiClient())

    handled = bot.process_update(
        {"message": {"chat": {"id": 123}, "text": "/help"}}
    )

    assert handled is True
    assert telegram.sent_messages == [
        (
            123,
            "Available commands:\n"
            "/start - start using LinguaFoundry\n"
            "/help - show available commands",
        )
    ]


def test_unknown_command_sends_help_hint() -> None:
    telegram = RecordingTelegramClient()
    bot = TelegramBotAdapter(telegram, HealthyApiClient())

    handled = bot.process_update(
        {"message": {"chat": {"id": 123}, "text": "/practice"}}
    )

    assert handled is True
    assert telegram.sent_messages == [
        (123, "Unknown command. Use /help to see available commands.")
    ]


def test_non_command_text_is_ignored() -> None:
    telegram = RecordingTelegramClient()
    bot = TelegramBotAdapter(telegram, HealthyApiClient())

    handled = bot.process_update(
        {"message": {"chat": {"id": 123}, "text": "hello"}}
    )

    assert handled is False
    assert telegram.sent_messages == []


def test_start_command_reports_api_connectivity_failure() -> None:
    telegram = RecordingTelegramClient()
    bot = TelegramBotAdapter(telegram, UnreachableApiClient())

    handled = bot.process_update(
        {"message": {"chat": {"id": 123}, "text": "/start"}}
    )

    assert handled is True
    assert telegram.sent_messages == [
        (
            123,
            "Welcome to LinguaFoundry. Use /help to see available commands.\n\n"
            "The learning API is not reachable yet, "
            "so practice is temporarily unavailable.",
        )
    ]
