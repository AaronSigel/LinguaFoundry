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
    UserProgressStats,
    calculate_user_progress_stats,
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


def test_user_progress_stats_are_calculated_from_attempts_and_progress() -> None:
    first_attempt_at = datetime(2026, 1, 1, 9, tzinfo=timezone.utc)
    last_attempt_at = datetime(2026, 1, 2, 10, tzinfo=timezone.utc)
    progress_attempt_at = datetime(2026, 1, 3, 11, tzinfo=timezone.utc)

    stats = calculate_user_progress_stats(
        "user-1",
        attempts=(
            Attempt(
                id="attempt-1",
                user_id="user-1",
                exercise_id="exercise-1",
                submitted_answer="hola",
                result=AttemptResult.CORRECT,
                attempted_at=first_attempt_at,
            ),
            Attempt(
                id="attempt-2",
                user_id="user-1",
                exercise_id="exercise-2",
                submitted_answer="adios",
                result=AttemptResult.INCORRECT,
                attempted_at=last_attempt_at,
            ),
            Attempt(
                id="attempt-3",
                user_id="user-1",
                exercise_id="exercise-3",
                submitted_answer="",
                result=AttemptResult.SKIPPED,
                attempted_at=progress_attempt_at,
            ),
            Attempt(
                id="attempt-other",
                user_id="user-2",
                exercise_id="exercise-1",
                submitted_answer="hola",
                result=AttemptResult.CORRECT,
            ),
        ),
        progress_entries=(
            Progress(
                user_id="user-1",
                lesson_id="lesson-1",
                status=CompletionStatus.COMPLETED,
                completed_exercises=2,
                total_exercises=2,
                last_attempt_at=last_attempt_at,
            ),
            Progress(
                user_id="user-1",
                lesson_id="lesson-2",
                status=CompletionStatus.IN_PROGRESS,
                completed_exercises=1,
                total_exercises=3,
                last_attempt_at=progress_attempt_at,
            ),
            Progress(
                user_id="user-2",
                lesson_id="lesson-3",
                status=CompletionStatus.COMPLETED,
                completed_exercises=1,
                total_exercises=1,
            ),
        ),
    )

    assert stats == UserProgressStats(
        user_id="user-1",
        answer_count=2,
        accuracy=0.5,
        completed_lessons=1,
        active_repetitions=1,
        last_activity_at=progress_attempt_at,
    )
    assert stats.accuracy_percent == 50.0


def test_user_progress_stats_defaults_for_no_activity() -> None:
    stats = calculate_user_progress_stats("user-1")

    assert stats == UserProgressStats(user_id="user-1")


def test_user_progress_stats_reject_invalid_values() -> None:
    with pytest.raises(ValueError, match="accuracy must be between"):
        UserProgressStats(user_id="user-1", accuracy=1.1)
