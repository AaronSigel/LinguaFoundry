"""Learning domain entities shared by LinguaFoundry services."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


def _require_non_empty(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} must not be empty")


class CEFRLevel(str, Enum):
    """Common European Framework of Reference language levels."""

    A1 = "A1"
    A2 = "A2"
    B1 = "B1"
    B2 = "B2"
    C1 = "C1"
    C2 = "C2"


class ExerciseType(str, Enum):
    """Supported exercise formats."""

    FLASHCARD = "flashcard"
    MULTIPLE_CHOICE = "multiple_choice"
    TEXT_INPUT = "text_input"
    TRANSLATION = "translation"


class AttemptResult(str, Enum):
    """Outcome recorded for a submitted exercise attempt."""

    CORRECT = "correct"
    INCORRECT = "incorrect"
    SKIPPED = "skipped"


class CompletionStatus(str, Enum):
    """Progress status for lessons, exercises, and sessions."""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


@dataclass(frozen=True, slots=True)
class User:
    """A learner using LinguaFoundry."""

    id: str
    display_name: str
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        _require_non_empty(self.id, "id")
        _require_non_empty(self.display_name, "display_name")


@dataclass(frozen=True, slots=True)
class Language:
    """A language available for study."""

    code: str
    name: str

    def __post_init__(self) -> None:
        _require_non_empty(self.code, "code")
        _require_non_empty(self.name, "name")
        object.__setattr__(self, "code", self.code.lower())


@dataclass(frozen=True, slots=True)
class Lesson:
    """A lesson within a language and proficiency level."""

    id: str
    language_code: str
    level: CEFRLevel
    title: str
    description: str = ""
    order: int = 0

    def __post_init__(self) -> None:
        _require_non_empty(self.id, "id")
        _require_non_empty(self.language_code, "language_code")
        _require_non_empty(self.title, "title")
        if self.order < 0:
            raise ValueError("order must be non-negative")
        object.__setattr__(self, "language_code", self.language_code.lower())


@dataclass(frozen=True, slots=True)
class Exercise:
    """A unit of practice inside a lesson."""

    id: str
    lesson_id: str
    exercise_type: ExerciseType
    prompt: str
    expected_answer: str
    order: int = 0

    def __post_init__(self) -> None:
        _require_non_empty(self.id, "id")
        _require_non_empty(self.lesson_id, "lesson_id")
        _require_non_empty(self.prompt, "prompt")
        _require_non_empty(self.expected_answer, "expected_answer")
        if self.order < 0:
            raise ValueError("order must be non-negative")


@dataclass(frozen=True, slots=True)
class Attempt:
    """A learner's submitted answer for an exercise."""

    id: str
    user_id: str
    exercise_id: str
    submitted_answer: str
    result: AttemptResult
    attempted_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        _require_non_empty(self.id, "id")
        _require_non_empty(self.user_id, "user_id")
        _require_non_empty(self.exercise_id, "exercise_id")
        if self.result is not AttemptResult.SKIPPED:
            _require_non_empty(self.submitted_answer, "submitted_answer")


@dataclass(frozen=True, slots=True)
class LearningSession:
    """A bounded study session for a learner and lesson."""

    id: str
    user_id: str
    lesson_id: str
    status: CompletionStatus = CompletionStatus.NOT_STARTED
    started_at: datetime = field(default_factory=utc_now)
    completed_at: datetime | None = None

    def __post_init__(self) -> None:
        _require_non_empty(self.id, "id")
        _require_non_empty(self.user_id, "user_id")
        _require_non_empty(self.lesson_id, "lesson_id")
        if self.status is CompletionStatus.COMPLETED and self.completed_at is None:
            raise ValueError("completed_at is required when status is completed")
        if self.completed_at is not None and self.completed_at < self.started_at:
            raise ValueError("completed_at must not be earlier than started_at")


@dataclass(frozen=True, slots=True)
class Progress:
    """Aggregated learner progress for a lesson."""

    user_id: str
    lesson_id: str
    status: CompletionStatus = CompletionStatus.NOT_STARTED
    completed_exercises: int = 0
    total_exercises: int = 0
    last_attempt_at: datetime | None = None

    def __post_init__(self) -> None:
        _require_non_empty(self.user_id, "user_id")
        _require_non_empty(self.lesson_id, "lesson_id")
        if self.completed_exercises < 0:
            raise ValueError("completed_exercises must be non-negative")
        if self.total_exercises < 0:
            raise ValueError("total_exercises must be non-negative")
        if self.completed_exercises > self.total_exercises:
            raise ValueError("completed_exercises must not exceed total_exercises")
        if (
            self.status is CompletionStatus.COMPLETED
            and self.completed_exercises != self.total_exercises
        ):
            raise ValueError("completed progress must include all exercises")

    @property
    def completion_ratio(self) -> float:
        """Return progress as a value from 0.0 to 1.0."""
        if self.total_exercises == 0:
            return 0.0
        return self.completed_exercises / self.total_exercises
