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
    "/lessons - list available lessons\n"
    "/lesson <lesson> - start a lesson\n"
    "/review - review missed exercises\n"
    "/progress - show your learning progress"
)
UNKNOWN_COMMAND_TEXT = "Unknown command. Use /help to see available commands."
REVIEW_COMMANDS = ("/review", "/mistakes", "/repeat_errors")


@dataclass(frozen=True)
class BotContext:
    """Dependencies available to command handlers."""

    api_client: ApiClient
    chat_sessions: dict[int, str]


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


def handle_lessons(message: IncomingMessage, context: BotContext) -> str:
    """Return available published lessons."""

    try:
        return _format_lesson_list(context.api_client.list_lessons())
    except ApiClientError:
        return (
            "Lessons are temporarily unavailable because the learning API "
            "cannot be reached."
        )


def handle_lesson(message: IncomingMessage, context: BotContext) -> str:
    """Start a lesson by id or slug and show the first exercise."""

    lesson_ref = _command_argument(message.text)
    if lesson_ref is None:
        return handle_lessons(message, context)

    try:
        user_id = _resolve_user_id(message, context)
        lesson = _find_lesson(context.api_client.list_lessons(), lesson_ref)
        if lesson is None:
            return f"Lesson '{lesson_ref}' was not found.\n\n" + _format_lesson_list(
                context.api_client.list_lessons()
            )
        lesson_id = _string_field(lesson, "id")
        session = context.api_client.start_session(user_id, lesson_id)
        session_id = _string_field(session, "session_id")
        context.chat_sessions[message.chat_id] = session_id
        exercise_payload = context.api_client.current_exercise(session_id)
    except ApiClientError:
        return (
            "Lesson practice is temporarily unavailable because the learning API "
            "cannot be reached."
        )

    return (
        f"Lesson started: {_string_field(lesson, 'title')}\n\n"
        f"{_format_current_exercise(exercise_payload, session)}"
    )


def handle_progress(message: IncomingMessage, context: BotContext) -> str:
    """Return a concise learning progress summary for the Telegram learner."""

    try:
        user_id = _resolve_user_id(message, context)
        stats = context.api_client.progress_stats(user_id)
    except ApiClientError:
        return (
            "Progress is temporarily unavailable because the learning API "
            "cannot be reached."
        )

    return _format_progress_stats(stats)


def handle_review(message: IncomingMessage, context: BotContext) -> str:
    """Return missed exercises that should be reviewed."""

    try:
        user_id = _resolve_user_id(message, context)
        review = context.api_client.review_queue(user_id)
    except ApiClientError:
        return (
            "Review is temporarily unavailable because the learning API "
            "cannot be reached."
        )

    cards = review.get("cards", [])
    if not isinstance(cards, list) or not cards:
        return "No mistakes to review yet. Missed exercises will appear here."

    lines = ["Review your missed exercises:"]
    for index, card in enumerate(cards, start=1):
        if not isinstance(card, dict):
            continue
        lines.append(f"{index}. {_string_field(card, 'prompt')}")
        expected_answer = _string_field(card, "expected_answer")
        if expected_answer:
            lines.append(f"Answer: {expected_answer}")
    return "\n".join(lines)


def create_router() -> CommandRouter:
    """Create the default bot command router."""

    router = CommandRouter()
    router.register("/start", handle_start)
    router.register("/help", handle_help)
    router.register("/lessons", handle_lessons)
    router.register("/lesson", handle_lesson)
    router.register("/progress", handle_progress)
    for command in REVIEW_COMMANDS:
        router.register(command, handle_review)
    return router


def handle_text_answer(message: IncomingMessage, context: BotContext) -> str:
    """Submit a plain text answer for the active chat session."""

    session_id = context.chat_sessions.get(message.chat_id)
    if session_id is None:
        try:
            lesson_list = _format_lesson_list(context.api_client.list_lessons())
        except ApiClientError:
            lesson_list = "Use /lessons to choose a lesson."
        return "Choose a lesson before sending an answer.\n\n" + lesson_list

    try:
        result = context.api_client.submit_answer(session_id, message.text.strip())
        progress = result.get("progress")
        exercise_payload = (
            {}
            if result.get("session_completed") is True
            else context.api_client.current_exercise(session_id)
        )
    except ApiClientError:
        return (
            "Answer submission is temporarily unavailable because the learning API "
            "cannot be reached."
        )

    lines = [_format_answer_result(result)]
    if result.get("session_completed") is True:
        context.chat_sessions.pop(message.chat_id, None)
        if isinstance(progress, dict):
            lines.append("")
            lines.append(_format_lesson_completion(progress))
        lines.append("Use /lessons to choose another lesson.")
        return "\n".join(lines)

    if isinstance(progress, dict):
        lines.append("")
        lines.append(_format_current_exercise(exercise_payload, progress))
    return "\n".join(lines)


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


def _resolve_user_id(message: IncomingMessage, context: BotContext) -> str:
    telegram_id = message.sender_id or message.chat_id
    user = context.api_client.register_telegram_user(telegram_id)
    return _string_field(user, "id")


def _format_lesson_list(lessons: list[dict[str, Any]]) -> str:
    if not lessons:
        return "No lessons are available yet."

    lines = ["Choose a lesson:"]
    for lesson in lessons:
        slug = _string_field(lesson, "slug")
        title = _string_field(lesson, "title")
        exercise_count = _int_stat(lesson, "exercise_count")
        suffix = f" ({exercise_count} exercises)" if exercise_count else ""
        lines.append(f"/lesson {slug} - {title}{suffix}")
    return "\n".join(lines)


def _find_lesson(
    lessons: list[dict[str, Any]],
    lesson_ref: str,
) -> dict[str, Any] | None:
    normalized = lesson_ref.casefold()
    for lesson in lessons:
        lesson_id = _string_field(lesson, "id")
        slug = _string_field(lesson, "slug")
        if normalized in {lesson_id.casefold(), slug.casefold()}:
            return lesson
    return None


def _format_current_exercise(
    exercise_payload: dict[str, Any],
    session_payload: dict[str, Any],
) -> str:
    exercise = exercise_payload.get("exercise")
    if not isinstance(exercise, dict):
        return "Lesson complete."

    completed = _int_stat(session_payload, "completed_exercises")
    total = _int_stat(session_payload, "total_exercises")
    number = completed + 1
    prefix = f"Exercise {number}/{total}" if total else f"Exercise {number}"
    return f"{prefix}\n{_string_field(exercise, 'prompt')}"


def _format_answer_result(result: dict[str, Any]) -> str:
    is_correct = result.get("is_correct")
    if is_correct is True:
        return "Correct."
    if is_correct is False:
        return "Incorrect."
    return "Answer recorded."


def _format_lesson_completion(progress: dict[str, Any]) -> str:
    completed = _int_stat(progress, "completed_exercises")
    total = _int_stat(progress, "total_exercises")
    return f"Lesson complete: {completed}/{total} exercises answered."


def _command_argument(text: str) -> str | None:
    parts = text.strip().split(maxsplit=1)
    if len(parts) == 1:
        return None
    argument = parts[1].strip()
    return argument or None


def _string_field(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise ApiClientError(f"API response did not include a valid {key}")
    return value


class TelegramBotAdapter:
    """Telegram update processor backed by command routing."""

    def __init__(
        self,
        telegram_client: TelegramClient,
        api_client: ApiClient,
        router: CommandRouter | None = None,
    ) -> None:
        self.telegram_client = telegram_client
        self.context = BotContext(api_client=api_client, chat_sessions={})
        self.router = router or create_router()

    def process_update(self, update: dict[str, object]) -> bool:
        """Process a single Telegram update and return whether it was handled."""

        message = parse_message(update)
        if message is None:
            return False

        response = self.router.dispatch(message, self.context)
        if response is None:
            response = handle_text_answer(message, self.context)

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
