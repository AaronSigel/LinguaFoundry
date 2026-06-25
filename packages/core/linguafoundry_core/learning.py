"""Learning session flow primitives.

The core package owns lesson orchestration without depending on Telegram,
HTTP, database clients, or language-pack storage formats.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from typing import Callable
from uuid import uuid4


REVIEW_INTERVAL_DAYS = (1, 3, 7, 14)


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""

    return datetime.now(timezone.utc)


class SessionStatus(StrEnum):
    """Lifecycle states for a learning session."""

    ACTIVE = "active"
    COMPLETED = "completed"


class SessionNotFoundError(LookupError):
    """Raised when a requested learning session does not exist."""


class ReviewItemNotFoundError(LookupError):
    """Raised when a requested review item does not exist."""


class ReviewSessionNotFoundError(LookupError):
    """Raised when a requested review session does not exist."""


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
class ReviewAnswerResult:
    """Result returned after checking a review-session answer."""

    review_item_id: str
    exercise_id: str
    submitted_answer: str
    correct: bool
    expected_answers: tuple[str, ...]
    explanation: str | None
    due_at: datetime
    incorrect_count: int
    session_completed: bool


@dataclass(frozen=True, slots=True)
class ReviewItem:
    """Exercise scheduled for later review after an incorrect answer."""

    id: str
    session_id: str
    exercise: Exercise
    due_at: datetime
    created_at: datetime
    incorrect_count: int = 1

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("Review item id is required.")
        if not self.session_id:
            raise ValueError("Review item session id is required.")
        if self.incorrect_count < 1:
            raise ValueError("Review item incorrect count must be positive.")
        if self.due_at.tzinfo is None:
            raise ValueError("Review item due_at must be timezone-aware.")
        if self.created_at.tzinfo is None:
            raise ValueError("Review item created_at must be timezone-aware.")


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


@dataclass(frozen=True, slots=True)
class ReviewSessionState:
    """Current state of a learner's progress through due review items."""

    id: str
    source_session_id: str
    review_item_ids: tuple[str, ...]
    current_index: int = 0
    correct_count: int = 0
    answered_count: int = 0
    status: SessionStatus = SessionStatus.ACTIVE

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("Review session id is required.")
        if not self.source_session_id:
            raise ValueError("Review session source session id is required.")
        if self.current_index < 0:
            raise ValueError("Review session current_index must be non-negative.")
        if self.correct_count < 0:
            raise ValueError("Review session correct_count must be non-negative.")
        if self.answered_count < 0:
            raise ValueError("Review session answered_count must be non-negative.")

    @property
    def current_review_item_id(self) -> str | None:
        if self.status == SessionStatus.COMPLETED:
            return None
        if self.current_index >= len(self.review_item_ids):
            return None
        return self.review_item_ids[self.current_index]


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


class InMemoryReviewStore:
    """Minimal in-memory review queue for early service integration."""

    def __init__(self) -> None:
        self._review_items: dict[str, ReviewItem] = {}

    def add(self, review_item: ReviewItem) -> None:
        self._review_items[review_item.id] = review_item

    def get(self, review_item_id: str) -> ReviewItem:
        try:
            return self._review_items[review_item_id]
        except KeyError as error:
            raise ReviewItemNotFoundError(review_item_id) from error

    def save(self, review_item: ReviewItem) -> None:
        if review_item.id not in self._review_items:
            raise ReviewItemNotFoundError(review_item.id)
        self._review_items[review_item.id] = review_item

    def find_for_exercise(self, session_id: str, exercise_id: str) -> ReviewItem | None:
        for review_item in self._review_items.values():
            if (
                review_item.session_id == session_id
                and review_item.exercise.id == exercise_id
            ):
                return review_item
        return None

    def due_items(self, session_id: str, due_at: datetime) -> tuple[ReviewItem, ...]:
        return tuple(
            sorted(
                (
                    review_item
                    for review_item in self._review_items.values()
                    if review_item.session_id == session_id
                    and review_item.due_at <= due_at
                ),
                key=lambda review_item: (
                    review_item.due_at,
                    review_item.exercise.id,
                ),
            )
        )


class InMemoryReviewSessionStore:
    """Minimal in-memory review-session store for early integration."""

    def __init__(self) -> None:
        self._review_sessions: dict[str, ReviewSessionState] = {}

    def add(self, review_session: ReviewSessionState) -> None:
        self._review_sessions[review_session.id] = review_session

    def get(self, review_session_id: str) -> ReviewSessionState:
        try:
            return self._review_sessions[review_session_id]
        except KeyError as error:
            raise ReviewSessionNotFoundError(review_session_id) from error

    def save(self, review_session: ReviewSessionState) -> None:
        if review_session.id not in self._review_sessions:
            raise ReviewSessionNotFoundError(review_session.id)
        self._review_sessions[review_session.id] = review_session


class LearningSessionManager:
    """Coordinates the core lesson lifecycle."""

    def __init__(
        self,
        store: InMemoryLearningSessionStore | None = None,
        review_store: InMemoryReviewStore | None = None,
        review_session_store: InMemoryReviewSessionStore | None = None,
        now: Callable[[], datetime] = utc_now,
    ) -> None:
        self._store = store or InMemoryLearningSessionStore()
        self._review_store = review_store or InMemoryReviewStore()
        self._review_session_store = (
            review_session_store or InMemoryReviewSessionStore()
        )
        self._now = now

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
        if not correct:
            self._schedule_review(session.id, exercise)

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

    def get_due_review_items(
        self,
        session_id: str,
        due_at: datetime | None = None,
    ) -> tuple[ReviewItem, ...]:
        """Return review items due for the session."""

        self.get_session(session_id)
        return self._review_store.due_items(session_id, due_at or self._now())

    def get_due_review_exercises(
        self,
        session_id: str,
        due_at: datetime | None = None,
    ) -> tuple[Exercise, ...]:
        """Return exercises ready to be practiced again."""

        return tuple(
            review_item.exercise
            for review_item in self.get_due_review_items(session_id, due_at)
        )

    def start_review_session(
        self,
        session_id: str,
        due_at: datetime | None = None,
        *,
        limit: int = 5,
    ) -> ReviewSessionState:
        """Create a session over due review items for a completed lesson session."""

        if limit < 1:
            raise ValueError("limit must be positive.")

        self.get_session(session_id)
        review_items = self.get_due_review_items(session_id, due_at)[:limit]
        review_session = ReviewSessionState(
            id=str(uuid4()),
            source_session_id=session_id,
            review_item_ids=tuple(review_item.id for review_item in review_items),
            status=(SessionStatus.ACTIVE if review_items else SessionStatus.COMPLETED),
        )
        self._review_session_store.add(review_session)
        return review_session

    def get_review_session(self, review_session_id: str) -> ReviewSessionState:
        """Return the current review-session state."""

        return self._review_session_store.get(review_session_id)

    def get_current_review_exercise(self, review_session_id: str) -> Exercise | None:
        """Return the review exercise waiting for an answer, or None when complete."""

        review_session = self.get_review_session(review_session_id)
        review_item_id = review_session.current_review_item_id
        if review_item_id is None:
            return None
        return self._review_store.get(review_item_id).exercise

    def submit_review_answer(
        self,
        review_session_id: str,
        answer: str,
    ) -> ReviewAnswerResult:
        """Check a review answer, reschedule the item, and advance the session."""

        review_session = self.get_review_session(review_session_id)
        review_item_id = review_session.current_review_item_id
        if review_item_id is None:
            raise ValueError("Cannot submit an answer to a completed review session.")

        review_item = self._review_store.get(review_item_id)
        exercise = review_item.exercise
        correct = _normalize(answer) in {
            _normalize(expected_answer) for expected_answer in exercise.correct_answers
        }
        reviewed_at = self._now()
        incorrect_count = review_item.incorrect_count + (0 if correct else 1)
        updated_review_item = replace(
            review_item,
            due_at=calculate_review_due_at(reviewed_at, incorrect_count),
            incorrect_count=incorrect_count,
        )
        self._review_store.save(updated_review_item)

        next_answered_count = review_session.answered_count + 1
        next_correct_count = review_session.correct_count + int(correct)
        next_index = review_session.current_index + 1
        completed = next_index >= len(review_session.review_item_ids)
        updated_review_session = replace(
            review_session,
            current_index=review_session.current_index if completed else next_index,
            correct_count=next_correct_count,
            answered_count=next_answered_count,
            status=SessionStatus.COMPLETED if completed else SessionStatus.ACTIVE,
        )
        self._review_session_store.save(updated_review_session)

        return ReviewAnswerResult(
            review_item_id=updated_review_item.id,
            exercise_id=exercise.id,
            submitted_answer=answer,
            correct=correct,
            expected_answers=exercise.correct_answers,
            explanation=exercise.explanation,
            due_at=updated_review_item.due_at,
            incorrect_count=updated_review_item.incorrect_count,
            session_completed=completed,
        )

    def _schedule_review(self, session_id: str, exercise: Exercise) -> ReviewItem:
        reviewed_at = self._now()
        existing_item = self._review_store.find_for_exercise(session_id, exercise.id)
        incorrect_count = (
            existing_item.incorrect_count + 1 if existing_item is not None else 1
        )
        review_item = ReviewItem(
            id=existing_item.id if existing_item is not None else str(uuid4()),
            session_id=session_id,
            exercise=exercise,
            due_at=calculate_review_due_at(reviewed_at, incorrect_count),
            created_at=(
                existing_item.created_at if existing_item is not None else reviewed_at
            ),
            incorrect_count=incorrect_count,
        )
        if existing_item is None:
            self._review_store.add(review_item)
        else:
            self._review_store.save(review_item)
        return review_item


def calculate_review_due_at(
    reviewed_at: datetime, incorrect_count: int = 1
) -> datetime:
    """Calculate the next lightweight SRS review timestamp."""

    if reviewed_at.tzinfo is None:
        raise ValueError("reviewed_at must be timezone-aware.")
    if incorrect_count < 1:
        raise ValueError("incorrect_count must be positive.")

    interval_index = min(incorrect_count - 1, len(REVIEW_INTERVAL_DAYS) - 1)
    return reviewed_at + timedelta(days=REVIEW_INTERVAL_DAYS[interval_index])


def _normalize(answer: str) -> str:
    return " ".join(answer.casefold().strip().split())
