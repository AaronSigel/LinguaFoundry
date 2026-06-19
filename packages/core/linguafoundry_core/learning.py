"""Learning session flow primitives.

The core package owns lesson orchestration without depending on Telegram,
HTTP, database clients, or language-pack storage formats.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from uuid import uuid4


class SessionStatus(StrEnum):
    """Lifecycle states for a learning session."""

    ACTIVE = "active"
    COMPLETED = "completed"


class SessionNotFoundError(LookupError):
    """Raised when a requested learning session does not exist."""


@dataclass(frozen=True, slots=True)
class Exercise:
    """A single lesson exercise with one or more accepted answers."""

    id: str
    prompt: str
    correct_answers: tuple[str, ...]
    explanation: str | None = None

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("Exercise id is required.")
        if not self.prompt:
            raise ValueError("Exercise prompt is required.")
        if not self.correct_answers:
            raise ValueError("At least one correct answer is required.")


@dataclass(frozen=True, slots=True)
class Lesson:
    """Ordered set of exercises that can be studied as a session."""

    id: str
    title: str
    exercises: tuple[Exercise, ...]

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("Lesson id is required.")
        if not self.title:
            raise ValueError("Lesson title is required.")
        if not self.exercises:
            raise ValueError("Lesson must include at least one exercise.")


@dataclass(frozen=True, slots=True)
class AnswerResult:
    """Result returned after checking an answer."""

    exercise_id: str
    submitted_answer: str
    correct: bool
    expected_answers: tuple[str, ...]
    explanation: str | None
    session_completed: bool


@dataclass(frozen=True, slots=True)
class SessionState:
    """Current state of a learner's progress through a lesson."""

    id: str
    lesson: Lesson
    current_index: int = 0
    correct_count: int = 0
    answered_count: int = 0
    status: SessionStatus = SessionStatus.ACTIVE

    @property
    def current_exercise(self) -> Exercise | None:
        if self.status == SessionStatus.COMPLETED:
            return None
        return self.lesson.exercises[self.current_index]


class InMemoryLearningSessionStore:
    """Minimal store useful for tests and early service integration."""

    def __init__(self) -> None:
        self._sessions: dict[str, SessionState] = {}

    def add(self, session: SessionState) -> None:
        self._sessions[session.id] = session

    def get(self, session_id: str) -> SessionState:
        try:
            return self._sessions[session_id]
        except KeyError as error:
            raise SessionNotFoundError(session_id) from error

    def save(self, session: SessionState) -> None:
        if session.id not in self._sessions:
            raise SessionNotFoundError(session.id)
        self._sessions[session.id] = session


class LearningSessionManager:
    """Coordinates the core lesson lifecycle."""

    def __init__(self, store: InMemoryLearningSessionStore | None = None) -> None:
        self._store = store or InMemoryLearningSessionStore()

    def start_lesson(self, lesson: Lesson) -> SessionState:
        """Create an active session for a lesson."""

        session = SessionState(id=str(uuid4()), lesson=lesson)
        self._store.add(session)
        return session

    def get_session(self, session_id: str) -> SessionState:
        """Return the current session state."""

        return self._store.get(session_id)

    def get_current_exercise(self, session_id: str) -> Exercise | None:
        """Return the exercise waiting for an answer, or None when complete."""

        return self.get_session(session_id).current_exercise

    def submit_answer(self, session_id: str, answer: str) -> AnswerResult:
        """Check an answer, record progress, and advance the session."""

        session = self.get_session(session_id)
        exercise = session.current_exercise
        if exercise is None:
            raise ValueError("Cannot submit an answer to a completed session.")

        correct = _normalize(answer) in {
            _normalize(expected_answer) for expected_answer in exercise.correct_answers
        }
        next_answered_count = session.answered_count + 1
        next_correct_count = session.correct_count + int(correct)
        next_index = session.current_index + 1
        completed = next_index >= len(session.lesson.exercises)

        updated_session = replace(
            session,
            current_index=session.current_index if completed else next_index,
            correct_count=next_correct_count,
            answered_count=next_answered_count,
            status=SessionStatus.COMPLETED if completed else SessionStatus.ACTIVE,
        )
        self._store.save(updated_session)

        return AnswerResult(
            exercise_id=exercise.id,
            submitted_answer=answer,
            correct=correct,
            expected_answers=exercise.correct_answers,
            explanation=exercise.explanation,
            session_completed=completed,
        )

    def complete_lesson(self, session_id: str) -> SessionState:
        """Mark a session complete, even if not all exercises were answered."""

        session = self.get_session(session_id)
        completed_session = replace(session, status=SessionStatus.COMPLETED)
        self._store.save(completed_session)
        return completed_session


def _normalize(answer: str) -> str:
    return " ".join(answer.casefold().strip().split())
