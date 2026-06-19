from datetime import datetime, timedelta, timezone

import pytest

from linguafoundry_core import (
    Attempt,
    AttemptResult,
    Exercise,
    ExerciseType,
    build_mistake_review_queue,
)


def test_mistake_review_queue_returns_latest_uncorrected_misses() -> None:
    base_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
    exercises = (
        _exercise("hello", "Translate: hello", "hola"),
        _exercise("thanks", "Translate: thank you", "gracias"),
        _exercise("bye", "Translate: goodbye", "adios"),
    )
    attempts = (
        _attempt("a1", "user-1", "hello", AttemptResult.INCORRECT, base_time),
        _attempt(
            "a2",
            "user-1",
            "thanks",
            AttemptResult.INCORRECT,
            base_time + timedelta(minutes=1),
        ),
        _attempt(
            "a3",
            "user-1",
            "hello",
            AttemptResult.CORRECT,
            base_time + timedelta(minutes=2),
        ),
        _attempt(
            "a4",
            "user-2",
            "bye",
            AttemptResult.INCORRECT,
            base_time + timedelta(minutes=3),
        ),
        _attempt(
            "a5",
            "user-1",
            "bye",
            AttemptResult.SKIPPED,
            base_time + timedelta(minutes=4),
        ),
    )

    queue = build_mistake_review_queue(attempts, exercises, "user-1")

    assert [card.exercise_id for card in queue] == ["thanks"]
    assert queue[0].prompt == "Translate: thank you"
    assert queue[0].expected_answer == "gracias"


def test_mistake_review_queue_counts_repeat_misses_and_applies_limit() -> None:
    base_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
    exercises = (
        _exercise("one", "One", "uno"),
        _exercise("two", "Two", "dos"),
    )
    attempts = (
        _attempt("a1", "user-1", "one", AttemptResult.INCORRECT, base_time),
        _attempt(
            "a2",
            "user-1",
            "one",
            AttemptResult.INCORRECT,
            base_time + timedelta(minutes=1),
        ),
        _attempt(
            "a3",
            "user-1",
            "two",
            AttemptResult.INCORRECT,
            base_time + timedelta(minutes=2),
        ),
    )

    queue = build_mistake_review_queue(
        attempts=attempts,
        exercises=exercises,
        user_id="user-1",
        limit=1,
    )

    assert [card.exercise_id for card in queue] == ["one"]
    assert queue[0].incorrect_attempts == 2


def test_mistake_review_queue_rejects_non_positive_limit() -> None:
    with pytest.raises(ValueError, match="limit must be positive"):
        build_mistake_review_queue((), (), "user-1", limit=0)


def _exercise(exercise_id: str, prompt: str, expected_answer: str) -> Exercise:
    return Exercise(
        id=exercise_id,
        lesson_id="lesson-1",
        exercise_type=ExerciseType.TEXT_INPUT,
        prompt=prompt,
        expected_answer=expected_answer,
    )


def _attempt(
    attempt_id: str,
    user_id: str,
    exercise_id: str,
    result: AttemptResult,
    attempted_at: datetime,
) -> Attempt:
    return Attempt(
        id=attempt_id,
        user_id=user_id,
        exercise_id=exercise_id,
        submitted_answer="answer",
        result=result,
        attempted_at=attempted_at,
    )
