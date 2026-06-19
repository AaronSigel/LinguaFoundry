import pytest

from linguafoundry_core import (
    LearningSessionManager,
    SessionNotFoundError,
    SessionStatus,
)
from linguafoundry_core.learning import Exercise, Lesson


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


def test_complete_lesson_stops_exercise_delivery() -> None:
    lesson = Lesson(
        id="intro",
        title="Intro",
        exercises=(
            Exercise(id="one", prompt="One", correct_answers=("one",)),
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
            (Exercise(id="one", prompt="Prompt", correct_answers=("a",)),),
        ),
        (
            "lesson",
            "",
            (Exercise(id="one", prompt="Prompt", correct_answers=("a",)),),
        ),
        ("lesson", "Title", ()),
    ],
)
def test_lesson_requires_identity_title_and_exercises(
    lesson_id: str,
    title: str,
    exercises: tuple[Exercise, ...],
) -> None:
    with pytest.raises(ValueError):
        Lesson(id=lesson_id, title=title, exercises=exercises)
