from datetime import datetime, timedelta, timezone

import pytest

from linguafoundry_core import (
    LearningExercise as Exercise,
    LearningLesson as Lesson,
    LearningSessionManager,
from linguafoundry_core.learning import (
    Exercise,
    LearningSessionManager,
    Lesson,
    SessionNotFoundError,
    SessionStatus,
    calculate_review_due_at,
)


FROZEN_NOW = datetime(2026, 6, 19, 12, 0, tzinfo=timezone.utc)


def test_learning_session_runs_through_lesson_flow() -> None:
    lesson = Lesson(
        id="intro-ru",
        title="Intro Russian",
        exercises=(
            Exercise(
                id="hello",
                prompt="Translate: hello",
                correct_answers=("privet", "привет"),
                explanation="Privet is an informal greeting.",
            ),
            Exercise(
                id="thanks",
                prompt="Translate: thank you",
                correct_answers=("spasibo", "спасибо"),
            ),
        ),
    )
    manager = LearningSessionManager()

    session = manager.start_lesson(lesson)

    assert session.status == SessionStatus.ACTIVE
    assert manager.get_current_exercise(session.id) == lesson.exercises[0]

    first_result = manager.submit_answer(session.id, "  PRIVET ")

    assert first_result.correct is True
    assert first_result.session_completed is False
    assert first_result.explanation == "Privet is an informal greeting."
    assert manager.get_current_exercise(session.id) == lesson.exercises[1]

    second_result = manager.submit_answer(session.id, "wrong")
    completed_session = manager.get_session(session.id)

    assert second_result.correct is False
    assert second_result.session_completed is True
    assert completed_session.status == SessionStatus.COMPLETED
    assert completed_session.answered_count == 2
    assert completed_session.correct_count == 1
    assert manager.get_current_exercise(session.id) is None


def test_incorrect_answer_creates_review_item_due_after_one_day() -> None:
    lesson = Lesson(
        id="intro",
        title="Intro",
        exercises=(
            Exercise(
                id="hello",
                prompt="Translate: hello",
                correct_answers=("hola",),
            ),
        ),
    )
    manager = LearningSessionManager(now=lambda: FROZEN_NOW)
    session = manager.start_lesson(lesson)

    result = manager.submit_answer(session.id, "bonjour")
    review_items = manager.get_due_review_items(
        session.id,
        due_at=FROZEN_NOW + timedelta(days=1),
    )

    assert result.correct is False
    assert len(review_items) == 1
    assert review_items[0].exercise == lesson.exercises[0]
    assert review_items[0].created_at == FROZEN_NOW
    assert review_items[0].due_at == FROZEN_NOW + timedelta(days=1)
    assert review_items[0].incorrect_count == 1


def test_due_review_exercises_excludes_items_before_due_date() -> None:
    lesson = Lesson(
        id="intro",
        title="Intro",
        exercises=(
            Exercise(
                id="hello",
                prompt="Translate: hello",
                correct_answers=("hola",),
            ),
        ),
    )
    manager = LearningSessionManager(now=lambda: FROZEN_NOW)
    session = manager.start_lesson(lesson)
    manager.submit_answer(session.id, "bonjour")

    assert manager.get_due_review_exercises(session.id, due_at=FROZEN_NOW) == ()
    assert manager.get_due_review_exercises(
        session.id,
        due_at=FROZEN_NOW + timedelta(days=1),
    ) == (lesson.exercises[0],)


def test_repeated_incorrect_answer_reschedules_existing_review_item() -> None:
    timestamps = iter(
        (
            FROZEN_NOW,
            FROZEN_NOW + timedelta(hours=1),
        )
    )
    lesson = Lesson(
        id="intro",
        title="Intro",
        exercises=(
            Exercise(
                id="hello",
                prompt="Translate: hello",
                correct_answers=("hola",),
            ),
            Exercise(
                id="hello",
                prompt="Translate again: hello",
                correct_answers=("hola",),
            ),
        ),
    )
    manager = LearningSessionManager(now=lambda: next(timestamps))

    session = manager.start_lesson(lesson)
    manager.submit_answer(session.id, "bonjour")
    first_review_item = manager.get_due_review_items(
        session.id,
        due_at=FROZEN_NOW + timedelta(days=1),
    )[0]

    manager.submit_answer(session.id, "ciao")
    review_items = manager.get_due_review_items(
        session.id,
        due_at=FROZEN_NOW + timedelta(days=3, hours=1),
    )

    assert len(review_items) == 1
    assert review_items[0].id == first_review_item.id
    assert review_items[0].created_at == FROZEN_NOW
    assert review_items[0].due_at == FROZEN_NOW + timedelta(days=3, hours=1)
    assert review_items[0].incorrect_count == 2


def test_review_due_date_uses_srs_lite_intervals() -> None:
    assert calculate_review_due_at(FROZEN_NOW, incorrect_count=1) == (
        FROZEN_NOW + timedelta(days=1)
    )
    assert calculate_review_due_at(FROZEN_NOW, incorrect_count=2) == (
        FROZEN_NOW + timedelta(days=3)
    )
    assert calculate_review_due_at(FROZEN_NOW, incorrect_count=3) == (
        FROZEN_NOW + timedelta(days=7)
    )
    assert calculate_review_due_at(FROZEN_NOW, incorrect_count=99) == (
        FROZEN_NOW + timedelta(days=14)
    )


def test_complete_lesson_stops_exercise_delivery() -> None:
    lesson = Lesson(
        id="intro",
        title="Intro",
        exercises=(
            Exercise(
                id="one",
                prompt="One",
                correct_answers=("one",),
            ),
        ),
    )
    manager = LearningSessionManager()
    session = manager.start_lesson(lesson)

    completed_session = manager.complete_lesson(session.id)

    assert completed_session.status == SessionStatus.COMPLETED
    assert manager.get_current_exercise(session.id) is None
    with pytest.raises(ValueError, match="completed session"):
        manager.submit_answer(session.id, "one")


def test_unknown_session_raises_domain_error() -> None:
    manager = LearningSessionManager()

    with pytest.raises(SessionNotFoundError):
        manager.get_current_exercise("missing")


@pytest.mark.parametrize(
    ("lesson_id", "title", "exercises"),
    [
        (
            "",
            "Title",
            (
                Exercise(
                    id="one",
                    prompt="Prompt",
                    correct_answers=("a",),
                ),
            ),
        ),
        (
            "lesson",
            "",
            (
                Exercise(
                    id="one",
                    prompt="Prompt",
                    correct_answers=("a",),
                ),
            ),
        ),
        (
            "lesson",
            "Title",
            (),
        ),
    ],
)
def test_lesson_requires_identity_title_and_exercises(
    lesson_id: str,
    title: str,
    exercises: tuple[Exercise, ...],
) -> None:
    with pytest.raises(ValueError):
        Lesson(id=lesson_id, title=title, exercises=exercises)
