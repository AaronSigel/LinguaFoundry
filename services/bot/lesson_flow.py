"""Telegram lesson flow orchestration."""

from __future__ import annotations

from dataclasses import dataclass

from linguafoundry_core.learning import LearningSessionManager

from services.bot.lesson_catalog import LessonCatalog, LessonNotFoundError


@dataclass(frozen=True, slots=True)
class BotReply:
    """Text response to send back to a Telegram chat."""

    chat_id: int
    text: str


class TelegramLessonFlow:
    """Handle lesson selection, answers, results, and lesson progression."""

    def __init__(
        self,
        catalog: LessonCatalog,
        session_manager: LearningSessionManager | None = None,
    ) -> None:
        self._catalog = catalog
        self._sessions = session_manager or LearningSessionManager()
        self._chat_sessions: dict[int, str] = {}

    def handle_message(self, chat_id: int, text: str) -> BotReply:
        text = text.strip()
        if text in {"/start", "/lessons"}:
            return BotReply(chat_id=chat_id, text=self._format_lesson_list())
        if text == "/lesson" or text.startswith("/lesson "):
            return BotReply(chat_id=chat_id, text=self._start_lesson(chat_id, text))
        if text.startswith("/"):
            return BotReply(
                chat_id=chat_id,
                text="Unknown command. Use /lessons to choose a lesson.",
            )
        return BotReply(chat_id=chat_id, text=self._submit_answer(chat_id, text))

    def _format_lesson_list(self) -> str:
        lesson_lines = [
            f"/lesson {lesson.id} - {lesson.title}"
            for lesson in self._catalog.list_lessons()
        ]
        return "Choose a lesson:\n" + "\n".join(lesson_lines)

    def _start_lesson(self, chat_id: int, command_text: str) -> str:
        parts = command_text.split(maxsplit=1)
        if len(parts) == 1:
            return self._format_lesson_list()

        lesson_id = parts[1].strip()
        try:
            lesson = self._catalog.get(lesson_id)
        except LessonNotFoundError:
            return (
                f"Lesson '{lesson_id}' was not found.\n\n"
                f"{self._format_lesson_list()}"
            )

        session = self._sessions.start_lesson(lesson)
        self._chat_sessions[chat_id] = session.id
        return (
            f"Lesson started: {lesson.title}\n\n"
            f"{self._format_current_exercise(session.id)}"
        )

    def _submit_answer(self, chat_id: int, answer: str) -> str:
        session_id = self._chat_sessions.get(chat_id)
        if session_id is None:
            return (
                "Choose a lesson before sending an answer.\n\n"
                + self._format_lesson_list()
            )

        result = self._sessions.submit_answer(session_id, answer)
        lines = ["Correct." if result.correct else "Incorrect."]
        if not result.correct:
            lines.append("Expected: " + ", ".join(result.expected_answers))
        if result.explanation:
            lines.append(result.explanation)

        if result.session_completed:
            session = self._sessions.get_session(session_id)
            self._chat_sessions.pop(chat_id, None)
            lines.append("")
            lines.append(
                "Lesson complete: "
                f"{session.correct_count}/{session.answered_count} correct."
            )
            lines.append("Use /lessons to choose another lesson.")
            return "\n".join(lines)

        lines.append("")
        lines.append(self._format_current_exercise(session_id))
        return "\n".join(lines)

    def _format_current_exercise(self, session_id: str) -> str:
        session = self._sessions.get_session(session_id)
        exercise = session.current_exercise
        if exercise is None:
            return "Lesson complete."
        total = len(session.lesson.exercises)
        exercise_number = session.current_index + 1
        return f"Exercise {exercise_number}/{total}\n{exercise.prompt}"
