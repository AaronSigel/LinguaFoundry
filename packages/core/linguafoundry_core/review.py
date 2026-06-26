"""Legacy in-memory review selection for missed exercises.

The production API builds review queues from durable ``ReviewState`` rows.
This module remains available for isolated core tests and prototype callers.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from linguafoundry_core.models import Attempt, AttemptResult, Exercise


@dataclass(frozen=True, slots=True)
class ReviewCard:
    """Exercise selected for mistake review."""

    exercise_id: str
    prompt: str
    expected_answer: str
    incorrect_attempts: int
    last_attempted_at: datetime


def build_mistake_review_queue(
    attempts: Iterable[Attempt],
    exercises: Iterable[Exercise],
    user_id: str,
    *,
    limit: int = 5,
) -> tuple[ReviewCard, ...]:
    """Return exercises the learner last answered incorrectly.

    This is intentionally small SRS-lite behavior: an exercise remains due for
    review when the learner's latest non-skipped attempt for it is incorrect.
    A later correct attempt removes it from the queue.
    """

    if limit < 1:
        raise ValueError("limit must be positive")

    exercise_by_id = {exercise.id: exercise for exercise in exercises}
    missed: dict[str, ReviewCard] = {}

    user_attempts = sorted(
        (attempt for attempt in attempts if attempt.user_id == user_id),
        key=lambda attempt: attempt.attempted_at,
    )
    for attempt in user_attempts:
        if attempt.result is AttemptResult.SKIPPED:
            continue
        if attempt.result is AttemptResult.CORRECT:
            missed.pop(attempt.exercise_id, None)
            continue

        exercise = exercise_by_id.get(attempt.exercise_id)
        if exercise is None:
            continue

        previous = missed.get(attempt.exercise_id)
        missed[attempt.exercise_id] = ReviewCard(
            exercise_id=exercise.id,
            prompt=exercise.prompt,
            expected_answer=exercise.expected_answer,
            incorrect_attempts=1
            if previous is None
            else previous.incorrect_attempts + 1,
            last_attempted_at=attempt.attempted_at,
        )

    return tuple(
        sorted(missed.values(), key=lambda card: card.last_attempted_at)[:limit]
    )
