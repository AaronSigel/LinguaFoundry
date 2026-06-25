import pytest

from services.bot.app.adapter import TelegramBotAdapter
from services.bot.app.api_client import ApiClientError


class RecordingTelegramClient:
    def __init__(self) -> None:
        self.sent_messages: list[tuple[int, str]] = []

    def send_message(self, chat_id: int, text: str) -> None:
        self.sent_messages.append((chat_id, text))


class HealthyApiClient:
    def __init__(self) -> None:
        self.answers: list[tuple[str, str]] = []
        self.registered_telegram_ids: list[int] = []
        self.started_sessions: list[tuple[str, str]] = []

    def health(self) -> dict[str, str]:
        return {"status": "ok"}

    def register_telegram_user(self, telegram_id: int) -> dict[str, str]:
        self.registered_telegram_ids.append(telegram_id)
        return {"id": f"user-{telegram_id}"}

    def progress_stats(self, user_id: str) -> dict[str, object]:
        return {
            "user_id": user_id,
            "answer_count": 8,
            "accuracy": 0.75,
            "accuracy_percent": 75.0,
            "completed_lessons": 2,
            "active_repetitions": 1,
            "last_activity_at": "2026-01-02T10:30:00+00:00",
        }

    def list_lessons(self) -> list[dict[str, object]]:
        return [
            {
                "id": "lesson-1",
                "slug": "intro",
                "title": "Intro",
                "exercise_count": 2,
            }
        ]

    def start_session(self, user_id: str, lesson_id: str) -> dict[str, object]:
        assert user_id == "user-456"
        assert lesson_id == "lesson-1"
        self.started_sessions.append((user_id, lesson_id))
        return {
            "session_id": "session-1",
            "user_id": user_id,
            "lesson_id": lesson_id,
            "status": "in_progress",
            "completed_exercises": 0,
            "total_exercises": 2,
        }

    def current_exercise(self, session_id: str) -> dict[str, object]:
        assert session_id == "session-1"
        if self.answers:
            return {
                "session_id": session_id,
                "status": "in_progress",
                "exercise": {
                    "id": "exercise-2",
                    "slug": "bye",
                    "kind": "text_input",
                    "prompt": "Translate: goodbye",
                    "payload": {},
                    "position": 2,
                },
            }
        return {
            "session_id": session_id,
            "status": "in_progress",
            "exercise": {
                "id": "exercise-1",
                "slug": "hello",
                "kind": "text_input",
                "prompt": "Translate: hello",
                "payload": {},
                "position": 1,
            },
        }

    def submit_answer(self, session_id: str, answer: str) -> dict[str, object]:
        self.answers.append((session_id, answer))
        completed = len(self.answers) == 2
        return {
            "attempt_id": f"attempt-{len(self.answers)}",
            "exercise_id": f"exercise-{len(self.answers)}",
            "is_correct": answer == "hola",
            "session_completed": completed,
            "progress": {
                "session_id": session_id,
                "user_id": "user-456",
                "lesson_id": "lesson-1",
                "status": "completed" if completed else "in_progress",
                "completed_exercises": len(self.answers),
                "total_exercises": 2,
            },
        }

    def review_queue(self, user_id: str) -> dict[str, object]:
        return {
            "user_id": user_id,
            "cards": [
                {
                    "exercise_id": "exercise-2",
                    "prompt": "Translate: goodbye",
                    "expected_answer": "adios",
                    "incorrect_attempts": 1,
                    "last_attempted_at": "2026-01-02T10:30:00+00:00",
                }
            ],
        }


class UnreachableApiClient:
    def health(self) -> dict[str, str]:
        raise ApiClientError("offline")

    def register_telegram_user(self, telegram_id: int) -> dict[str, str]:
        raise ApiClientError("offline")


class MultipleChoiceApiClient(HealthyApiClient):
    def current_exercise(self, session_id: str) -> dict[str, object]:
        assert session_id == "session-1"
        return {
            "session_id": session_id,
            "status": "in_progress",
            "exercise": {
                "id": "exercise-1",
                "slug": "choose-hello",
                "kind": "multiple_choice",
                "prompt": "Choose the Spanish greeting for hello.",
                "payload": {
                    "options": [
                        {"id": "hello", "text": "hola"},
                        {"id": "goodbye", "text": "adios"},
                    ]
                },
                "position": 1,
            },
        }


class MatchingOptionIdApiClient(HealthyApiClient):
    def current_exercise(self, session_id: str) -> dict[str, object]:
        assert session_id == "session-1"
        return {
            "session_id": session_id,
            "status": "in_progress",
            "exercise": {
                "id": "exercise-1",
                "slug": "choose-hello",
                "kind": "multiple_choice",
                "prompt": "Choose the Spanish greeting for hello.",
                "payload": {
                    "options": [
                        {"id": "hola", "text": "hola"},
                        {"id": "adios", "text": "adios"},
                    ]
                },
                "position": 1,
            },
        }


class FollowUpMultipleChoiceApiClient(HealthyApiClient):
    def current_exercise(self, session_id: str) -> dict[str, object]:
        assert session_id == "session-1"
        if not self.answers:
            return {
                "session_id": session_id,
                "status": "in_progress",
                "exercise": {
                    "id": "exercise-1",
                    "slug": "hello",
                    "kind": "text_input",
                    "prompt": "Translate: hello",
                    "payload": {},
                    "position": 1,
                },
            }
        return {
            "session_id": session_id,
            "status": "in_progress",
            "exercise": {
                "id": "exercise-2",
                "slug": "choose-goodbye",
                "kind": "multiple_choice",
                "prompt": "Choose the Spanish word for goodbye.",
                "payload": {
                    "options": [
                        {"id": "hello", "text": "hola"},
                        {"id": "goodbye", "text": "adios"},
                    ]
                },
                "position": 2,
            },
        }


def test_start_command_sends_welcome_message() -> None:
    telegram = RecordingTelegramClient()
    bot = TelegramBotAdapter(telegram, HealthyApiClient())

    handled = bot.process_update({"message": {"chat": {"id": 123}, "text": "/start"}})

    assert handled is True
    assert telegram.sent_messages == [
        (123, "Welcome to LinguaFoundry. Use /help to see available commands.")
    ]


def test_help_command_lists_available_commands() -> None:
    telegram = RecordingTelegramClient()
    bot = TelegramBotAdapter(telegram, HealthyApiClient())

    handled = bot.process_update({"message": {"chat": {"id": 123}, "text": "/help"}})

    assert handled is True
    assert telegram.sent_messages == [
        (
            123,
            "Available commands:\n"
            "/start - start using LinguaFoundry\n"
            "/help - show available commands\n"
            "/lessons - list available lessons\n"
            "/lesson <lesson> - start a lesson\n"
            "/review - review missed exercises\n"
            "/progress - show your learning progress",
        )
    ]


def test_lessons_command_lists_api_lessons() -> None:
    telegram = RecordingTelegramClient()
    bot = TelegramBotAdapter(telegram, HealthyApiClient())

    handled = bot.process_update({"message": {"chat": {"id": 123}, "text": "/lessons"}})

    assert handled is True
    assert telegram.sent_messages == [
        (123, "Choose a lesson:\n/lesson intro - Intro (2 exercises)")
    ]


def test_lesson_command_starts_api_session_and_text_answers_advance() -> None:
    telegram = RecordingTelegramClient()
    api_client = HealthyApiClient()
    bot = TelegramBotAdapter(telegram, api_client)

    bot.process_update(
        {
            "message": {
                "chat": {"id": 123},
                "from": {"id": 456},
                "text": "/lesson intro",
            }
        }
    )
    bot.process_update({"message": {"chat": {"id": 123}, "text": "hola"}})
    bot.process_update({"message": {"chat": {"id": 123}, "text": "wrong"}})

    assert telegram.sent_messages == [
        (
            123,
            "Lesson started: Intro\n\nExercise 1/2\nTranslate: hello",
        ),
        (
            123,
            "Correct.\n\nExercise 2/2\nTranslate: goodbye",
        ),
        (
            123,
            "Incorrect.\n\n"
            "Lesson complete: 2/2 exercises answered.\n"
            "Use /lessons to choose another lesson.",
        ),
    ]
    assert api_client.registered_telegram_ids == [456]
    assert api_client.started_sessions == [("user-456", "lesson-1")]
    assert api_client.answers == [("session-1", "hola"), ("session-1", "wrong")]


def test_lesson_command_renders_multiple_choice_options() -> None:
    telegram = RecordingTelegramClient()
    bot = TelegramBotAdapter(telegram, MultipleChoiceApiClient())

    handled = bot.process_update(
        {
            "message": {
                "chat": {"id": 123},
                "from": {"id": 456},
                "text": "/lesson intro",
            }
        }
    )

    assert handled is True
    assert telegram.sent_messages == [
        (
            123,
            "Lesson started: Intro\n\n"
            "Exercise 1/2\n"
            "Choose the Spanish greeting for hello.\n"
            "Options:\n"
            "1. hello - hola\n"
            "2. goodbye - adios",
        )
    ]


def test_lesson_command_does_not_duplicate_matching_multiple_choice_ids() -> None:
    telegram = RecordingTelegramClient()
    bot = TelegramBotAdapter(telegram, MatchingOptionIdApiClient())

    handled = bot.process_update(
        {
            "message": {
                "chat": {"id": 123},
                "from": {"id": 456},
                "text": "/lesson intro",
            }
        }
    )

    assert handled is True
    assert telegram.sent_messages == [
        (
            123,
            "Lesson started: Intro\n\n"
            "Exercise 1/2\n"
            "Choose the Spanish greeting for hello.\n"
            "Options:\n"
            "1. hola\n"
            "2. adios",
        )
    ]


def test_text_answer_renders_follow_up_multiple_choice_options() -> None:
    telegram = RecordingTelegramClient()
    bot = TelegramBotAdapter(telegram, FollowUpMultipleChoiceApiClient())

    bot.process_update(
        {
            "message": {
                "chat": {"id": 123},
                "from": {"id": 456},
                "text": "/lesson intro",
            }
        }
    )
    handled = bot.process_update({"message": {"chat": {"id": 123}, "text": "hola"}})

    assert handled is True
    assert telegram.sent_messages[-1] == (
        123,
        "Correct.\n\n"
        "Exercise 2/2\n"
        "Choose the Spanish word for goodbye.\n"
        "Options:\n"
        "1. hello - hola\n"
        "2. goodbye - adios",
    )


def test_text_answer_after_completed_lesson_requires_new_lesson() -> None:
    telegram = RecordingTelegramClient()
    bot = TelegramBotAdapter(telegram, HealthyApiClient())

    bot.process_update(
        {
            "message": {
                "chat": {"id": 123},
                "from": {"id": 456},
                "text": "/lesson intro",
            }
        }
    )
    bot.process_update({"message": {"chat": {"id": 123}, "text": "hola"}})
    bot.process_update({"message": {"chat": {"id": 123}, "text": "adios"}})

    handled = bot.process_update({"message": {"chat": {"id": 123}, "text": "otra"}})

    assert handled is True
    assert telegram.sent_messages[-1] == (
        123,
        "Choose a lesson before sending an answer.\n\n"
        "Choose a lesson:\n"
        "/lesson intro - Intro (2 exercises)",
    )


def test_text_answer_before_lesson_prompts_for_api_lesson_selection() -> None:
    telegram = RecordingTelegramClient()
    bot = TelegramBotAdapter(telegram, HealthyApiClient())

    handled = bot.process_update({"message": {"chat": {"id": 123}, "text": "hola"}})

    assert handled is True
    assert telegram.sent_messages == [
        (
            123,
            "Choose a lesson before sending an answer.\n\n"
            "Choose a lesson:\n"
            "/lesson intro - Intro (2 exercises)",
        )
    ]


@pytest.mark.parametrize("command", ["/review", "/mistakes", "/repeat_errors"])
def test_review_commands_use_api_review_queue(command: str) -> None:
    telegram = RecordingTelegramClient()
    bot = TelegramBotAdapter(telegram, HealthyApiClient())

    handled = bot.process_update(
        {
            "message": {
                "chat": {"id": 123},
                "from": {"id": 456},
                "text": command,
            }
        }
    )

    assert handled is True
    assert telegram.sent_messages == [
        (
            123,
            "Review your missed exercises:\n1. Translate: goodbye\nAnswer: adios",
        )
    ]


def test_progress_command_sends_learning_stats() -> None:
    telegram = RecordingTelegramClient()
    bot = TelegramBotAdapter(telegram, HealthyApiClient())

    handled = bot.process_update(
        {
            "message": {
                "chat": {"id": 123},
                "from": {"id": 456},
                "text": "/progress",
            }
        }
    )

    assert handled is True
    assert telegram.sent_messages == [
        (
            123,
            "Your learning progress:\n"
            "Answers: 8\n"
            "Accuracy: 75%\n"
            "Completed lessons: 2\n"
            "Active lessons: 1\n"
            "Last activity: 2026-01-02 10:30 UTC",
        )
    ]


def test_progress_command_reports_api_failure() -> None:
    telegram = RecordingTelegramClient()
    bot = TelegramBotAdapter(telegram, UnreachableApiClient())

    handled = bot.process_update(
        {
            "message": {
                "chat": {"id": 123},
                "from": {"id": 456},
                "text": "/progress",
            }
        }
    )

    assert handled is True
    assert telegram.sent_messages == [
        (
            123,
            "Progress is temporarily unavailable because the learning API "
            "cannot be reached.",
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


def test_non_command_text_uses_answer_flow() -> None:
    telegram = RecordingTelegramClient()
    bot = TelegramBotAdapter(telegram, HealthyApiClient())

    handled = bot.process_update({"message": {"chat": {"id": 123}, "text": "hello"}})

    assert handled is True
    assert telegram.sent_messages == [
        (
            123,
            "Choose a lesson before sending an answer.\n\n"
            "Choose a lesson:\n"
            "/lesson intro - Intro (2 exercises)",
        )
    ]


def test_start_command_reports_api_connectivity_failure() -> None:
    telegram = RecordingTelegramClient()
    bot = TelegramBotAdapter(telegram, UnreachableApiClient())

    handled = bot.process_update({"message": {"chat": {"id": 123}, "text": "/start"}})

    assert handled is True
    assert telegram.sent_messages == [
        (
            123,
            "Welcome to LinguaFoundry. Use /help to see available commands.\n\n"
            "The learning API is not reachable yet, "
            "so practice is temporarily unavailable.",
        )
    ]
