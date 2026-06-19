from datetime import datetime, timedelta, timezone

import pytest

from linguafoundry_core import (
    Attempt,
    AttemptResult,
    CEFRLevel,
    CompletionStatus,
    Exercise,
    ExerciseType,
    Language,
    LearningSession,
    Lesson,
    Progress,
    User,
)


def test_learning_domain_entities_can_be_created() -> None:
    user = User(id="user-1", display_name="Ada")
    language = Language(code="ES", name="Spanish")
    lesson = Lesson(
        id="lesson-1",
        language_code=language.code,
        level=CEFRLevel.A1,
        title="Greetings",
    )
    exercise = Exercise(
        id="exercise-1",
        lesson_id=lesson.id,
        exercise_type=ExerciseType.TEXT_INPUT,
        prompt="Translate: hello",
        expected_answer="hola",
    )
    attempt = Attempt(
        id="attempt-1",
        user_id=user.id,
        exercise_id=exercise.id,
        submitted_answer="hola",
        result=AttemptResult.CORRECT,
    )
    session = LearningSession(
        id="session-1",
        user_id=user.id,
        lesson_id=lesson.id,
        status=CompletionStatus.IN_PROGRESS,
    )
    progress = Progress(
        user_id=user.id,
        lesson_id=lesson.id,
        status=CompletionStatus.COMPLETED,
        completed_exercises=1,
        total_exercises=1,
        last_attempt_at=attempt.attempted_at,
    )

    assert language.code == "es"
    assert lesson.language_code == "es"
    assert session.completed_at is None
    assert progress.completion_ratio == 1.0


def test_completed_session_requires_completion_timestamp() -> None:
    with pytest.raises(ValueError, match="completed_at is required"):
        LearningSession(
            id="session-1",
            user_id="user-1",
            lesson_id="lesson-1",
            status=CompletionStatus.COMPLETED,
        )


def test_completed_at_cannot_precede_started_at() -> None:
    started_at = datetime(2026, 1, 1, tzinfo=timezone.utc)

    with pytest.raises(ValueError, match="completed_at must not be earlier"):
        LearningSession(
            id="session-1",
            user_id="user-1",
            lesson_id="lesson-1",
            status=CompletionStatus.COMPLETED,
            started_at=started_at,
            completed_at=started_at - timedelta(minutes=1),
        )


def test_progress_rejects_impossible_counts() -> None:
    with pytest.raises(ValueError, match="completed_exercises must not exceed"):
        Progress(
            user_id="user-1",
            lesson_id="lesson-1",
            status=CompletionStatus.IN_PROGRESS,
            completed_exercises=2,
            total_exercises=1,
        )


def test_completed_progress_requires_all_exercises() -> None:
    with pytest.raises(ValueError, match="completed progress"):
        Progress(
            user_id="user-1",
            lesson_id="lesson-1",
            status=CompletionStatus.COMPLETED,
            completed_exercises=1,
            total_exercises=2,
        )


def test_empty_required_values_are_rejected() -> None:
    with pytest.raises(ValueError, match="display_name must not be empty"):
        User(id="user-1", display_name=" ")
