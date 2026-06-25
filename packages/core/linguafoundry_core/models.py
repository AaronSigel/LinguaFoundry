"""Learning domain entities shared by LinguaFoundry services."""

from __future__ import annotations

from collections.abc import Iterable
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


class ReviewStatus(str, Enum):
    """Durable review lifecycle for exercises that need repetition."""

    ACTIVE = "active"
    MASTERED = "mastered"


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
    session_id: str | None = None
    language_pack_id: str | None = None
    language_pack_version: str | None = None
    attempted_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        _require_non_empty(self.id, "id")
        _require_non_empty(self.user_id, "user_id")
        _require_non_empty(self.exercise_id, "exercise_id")
        if self.session_id is not None:
            _require_non_empty(self.session_id, "session_id")
        if self.language_pack_id is not None:
            _require_non_empty(self.language_pack_id, "language_pack_id")
        if self.language_pack_version is not None:
            _require_non_empty(self.language_pack_version, "language_pack_version")
        if self.result is not AttemptResult.SKIPPED:
            _require_non_empty(self.submitted_answer, "submitted_answer")


@dataclass(frozen=True, slots=True)
class LearningSession:
    """A bounded study session for a learner and lesson."""

    id: str
    user_id: str
    lesson_id: str
    language_pack_id: str = "legacy"
    language_pack_version: str = "1.0"
    status: CompletionStatus = CompletionStatus.NOT_STARTED
    current_exercise_index: int = 0
    started_at: datetime = field(default_factory=utc_now)
    completed_at: datetime | None = None

    def __post_init__(self) -> None:
        _require_non_empty(self.id, "id")
        _require_non_empty(self.user_id, "user_id")
        _require_non_empty(self.lesson_id, "lesson_id")
        _require_non_empty(self.language_pack_id, "language_pack_id")
        _require_non_empty(self.language_pack_version, "language_pack_version")
        if self.current_exercise_index < 0:
            raise ValueError("current_exercise_index must be non-negative")
        if self.status is CompletionStatus.COMPLETED and self.completed_at is None:
            raise ValueError("completed_at is required when status is completed")
        if self.completed_at is not None and self.completed_at < self.started_at:
            raise ValueError("completed_at must not be earlier than started_at")


@dataclass(frozen=True, slots=True)
class ReviewState:
    """Durable review scheduling state for a learner and exercise."""

    user_id: str
    exercise_id: str
    lesson_id: str
    language_pack_id: str
    language_pack_version: str
    due_at: datetime
    status: ReviewStatus = ReviewStatus.ACTIVE
    incorrect_count: int = 1
    last_attempt_id: str | None = None
    session_id: str | None = None
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        _require_non_empty(self.user_id, "user_id")
        _require_non_empty(self.exercise_id, "exercise_id")
        _require_non_empty(self.lesson_id, "lesson_id")
        _require_non_empty(self.language_pack_id, "language_pack_id")
        _require_non_empty(self.language_pack_version, "language_pack_version")
        if self.last_attempt_id is not None:
            _require_non_empty(self.last_attempt_id, "last_attempt_id")
        if self.session_id is not None:
            _require_non_empty(self.session_id, "session_id")
        if self.incorrect_count < 1:
            raise ValueError("incorrect_count must be positive")
        if self.due_at.tzinfo is None:
            raise ValueError("due_at must be timezone-aware")
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")


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


@dataclass(frozen=True, slots=True)
class UserProgressStats:
    """Basic aggregate progress statistics for a learner."""

    user_id: str
    answer_count: int = 0
    accuracy: float = 0.0
    completed_lessons: int = 0
    active_repetitions: int = 0
    last_activity_at: datetime | None = None

    def __post_init__(self) -> None:
        _require_non_empty(self.user_id, "user_id")
        if self.answer_count < 0:
            raise ValueError("answer_count must be non-negative")
        if not 0.0 <= self.accuracy <= 1.0:
            raise ValueError("accuracy must be between 0.0 and 1.0")
        if self.completed_lessons < 0:
            raise ValueError("completed_lessons must be non-negative")
        if self.active_repetitions < 0:
            raise ValueError("active_repetitions must be non-negative")

    @property
    def accuracy_percent(self) -> float:
        """Return accuracy as a percentage from 0.0 to 100.0."""
        return self.accuracy * 100


def calculate_user_progress_stats(
    user_id: str,
    attempts: Iterable[Attempt] = (),
    progress_entries: Iterable[Progress] = (),
) -> UserProgressStats:
    """Build basic learner statistics from known attempts and lesson progress."""

    _require_non_empty(user_id, "user_id")

    user_attempts = [attempt for attempt in attempts if attempt.user_id == user_id]
    answered_attempts = [
        attempt
        for attempt in user_attempts
        if attempt.result in {AttemptResult.CORRECT, AttemptResult.INCORRECT}
    ]
    correct_answers = sum(
        1 for attempt in answered_attempts if attempt.result is AttemptResult.CORRECT
    )
    answer_count = len(answered_attempts)
    accuracy = correct_answers / answer_count if answer_count else 0.0

    user_progress_entries = [
        progress for progress in progress_entries if progress.user_id == user_id
    ]
    completed_lessons = sum(
        1
        for progress in user_progress_entries
        if progress.status is CompletionStatus.COMPLETED
    )
    active_repetitions = sum(
        1
        for progress in user_progress_entries
        if progress.status is CompletionStatus.IN_PROGRESS
    )
    activity_times = [
        activity_time
        for activity_time in (
            *(attempt.attempted_at for attempt in user_attempts),
            *(progress.last_attempt_at for progress in user_progress_entries),
        )
        if activity_time is not None
    ]

    return UserProgressStats(
        user_id=user_id,
        answer_count=answer_count,
        accuracy=accuracy,
        completed_lessons=completed_lessons,
        active_repetitions=active_repetitions,
        last_activity_at=max(activity_times, default=None),
    )
