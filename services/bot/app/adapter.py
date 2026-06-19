"""Command routing for the Telegram bot adapter."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from services.bot.app.api_client import ApiClient, ApiClientError
from services.bot.app.telegram import IncomingMessage, TelegramClient, parse_message


WELCOME_TEXT = "Welcome to LinguaFoundry. Use /help to see available commands."
HELP_TEXT = (
    "Available commands:\n"
    "/start - start using LinguaFoundry\n"
    "/help - show available commands\n"
    "/progress - show your learning progress"
)
UNKNOWN_COMMAND_TEXT = "Unknown command. Use /help to see available commands."


@dataclass(frozen=True)
class BotContext:
    """Dependencies available to command handlers."""

    api_client: ApiClient


Handler = Callable[[IncomingMessage, BotContext], str]


class CommandRouter:
    """Route Telegram commands to registered handlers."""

    def __init__(self) -> None:
        self._handlers: dict[str, Handler] = {}

    def register(self, command: str, handler: Handler) -> None:
        """Register a handler for a slash command."""

        normalized = command if command.startswith("/") else f"/{command}"
        self._handlers[normalized.lower()] = handler

    def dispatch(self, message: IncomingMessage, context: BotContext) -> str | None:
        """Return a handler response for a message, when one applies."""

        command = message.command
        if command is None:
            return None

        handler = self._handlers.get(command)
        if handler is None:
            return UNKNOWN_COMMAND_TEXT
        return handler(message, context)


def handle_start(message: IncomingMessage, context: BotContext) -> str:
    """Return the greeting for /start."""

    try:
        context.api_client.health()
    except ApiClientError:
        return (
            f"{WELCOME_TEXT}\n\n"
            "The learning API is not reachable yet, "
            "so practice is temporarily unavailable."
        )
    return WELCOME_TEXT


def handle_help(message: IncomingMessage, context: BotContext) -> str:
    """Return available bot commands."""

    return HELP_TEXT


def handle_progress(message: IncomingMessage, context: BotContext) -> str:
    """Return a concise learning progress summary for the Telegram learner."""

    telegram_id = message.sender_id or message.chat_id
    try:
        user = context.api_client.register_telegram_user(telegram_id)
        user_id = user.get("id")
        if not isinstance(user_id, str):
            raise ApiClientError("API response did not include a user id")
        stats = context.api_client.progress_stats(user_id)
    except ApiClientError:
        return (
            "Progress is temporarily unavailable because the learning API "
            "cannot be reached."
        )

    return _format_progress_stats(stats)


def create_router() -> CommandRouter:
    """Create the default bot command router."""

    router = CommandRouter()
    router.register("/start", handle_start)
    router.register("/help", handle_help)
    router.register("/progress", handle_progress)
    return router


def _format_progress_stats(stats: dict[str, Any]) -> str:
    answer_count = _int_stat(stats, "answer_count")
    accuracy_percent = _float_stat(stats, "accuracy_percent")
    completed_lessons = _int_stat(stats, "completed_lessons")
    active_repetitions = _int_stat(stats, "active_repetitions")

    return (
        "Your learning progress:\n"
        f"Answers: {answer_count}\n"
        f"Accuracy: {accuracy_percent:.0f}%\n"
        f"Completed lessons: {completed_lessons}\n"
        f"Active lessons: {active_repetitions}\n"
        f"Last activity: {_format_activity(stats.get('last_activity_at'))}"
    )


def _int_stat(stats: dict[str, Any], key: str) -> int:
    value = stats.get(key, 0)
    return value if isinstance(value, int) else 0


def _float_stat(stats: dict[str, Any], key: str) -> float:
    value = stats.get(key, 0.0)
    return float(value) if isinstance(value, int | float) else 0.0


def _format_activity(value: object) -> str:
    if not isinstance(value, str) or not value:
        return "no activity yet"

    normalized = value.removesuffix("Z") + "+00:00" if value.endswith("Z") else value
    try:
        activity_at = datetime.fromisoformat(normalized)
    except ValueError:
        return value

    if activity_at.tzinfo is None:
        return activity_at.strftime("%Y-%m-%d %H:%M")
    return activity_at.strftime("%Y-%m-%d %H:%M %Z").strip()


class TelegramBotAdapter:
    """Telegram update processor backed by command routing."""

    def __init__(
        self,
        telegram_client: TelegramClient,
        api_client: ApiClient,
        router: CommandRouter | None = None,
    ) -> None:
        self.telegram_client = telegram_client
        self.context = BotContext(api_client=api_client)
        self.router = router or create_router()

    def process_update(self, update: dict[str, object]) -> bool:
        """Process a single Telegram update and return whether it was handled."""

        message = parse_message(update)
        if message is None:
            return False

        response = self.router.dispatch(message, self.context)
        if response is None:
            return False

        self.telegram_client.send_message(message.chat_id, response)
        return True

    def run_polling(self, timeout: int) -> None:
        """Run a simple long-polling loop for local operation."""

        offset: int | None = None
        while True:
            updates = self.telegram_client.get_updates(offset=offset, timeout=timeout)
            for update in updates:
                update_id = update.get("update_id")
                if isinstance(update_id, int):
                    offset = update_id + 1
                self.process_update(update)
