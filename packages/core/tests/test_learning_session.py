from datetime import datetime, timedelta, timezone

import pytest

from linguafoundry_core.learning import (
    Exercise,
    LearningSessionManager,
    Lesson,
    ReviewSessionNotFoundError,
    SessionNotFoundError,
    SessionStatus,
)
from linguafoundry_core.answers import (
    check_answer,
    expected_answer_text,
    extract_accepted_answers,
)
from linguafoundry_core.review_schedule import (
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


def test_check_answer_accepts_normalized_answer_payload_variants() -> None:
    answer_payload = {"accepted_answers": ["Buenos dias", "Buen dia"]}

    assert check_answer("  buenos   DIAS ", answer_payload) is True
    assert check_answer("hola", answer_payload) is False


def test_check_answer_returns_none_without_accepted_answers() -> None:
    assert check_answer("hola", None) is None
    assert check_answer("hola", {}) is None


def test_answer_helpers_extract_and_format_answers() -> None:
    answer_payload = {"accepted_answers": ["hola", "buenas"]}

    assert extract_accepted_answers(answer_payload) == ("hola", "buenas")
    assert expected_answer_text(answer_payload) == "hola, buenas"
    assert expected_answer_text(None) == ""


def test_review_session_delivers_due_exercise_and_reschedules_correct_answer() -> None:
    timestamps = iter(
        (
            FROZEN_NOW,
            FROZEN_NOW + timedelta(days=1, minutes=5),
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
                explanation="Hola is a greeting.",
            ),
        ),
    )
    manager = LearningSessionManager(now=lambda: next(timestamps))
    session = manager.start_lesson(lesson)
    manager.submit_answer(session.id, "bonjour")

    review_session = manager.start_review_session(
        session.id,
        due_at=FROZEN_NOW + timedelta(days=1, minutes=1),
    )
    assert manager.get_current_review_exercise(review_session.id) == lesson.exercises[0]

    result = manager.submit_review_answer(review_session.id, " HOLA ")
    review_items = manager.get_due_review_items(
        session.id,
        due_at=FROZEN_NOW + timedelta(days=2, minutes=5),
    )
    completed_review_session = manager.get_review_session(review_session.id)

    assert review_session.status == SessionStatus.ACTIVE
    assert manager.get_current_review_exercise(review_session.id) is None
    assert result.correct is True
    assert result.explanation == "Hola is a greeting."
    assert result.incorrect_count == 1
    assert result.due_at == FROZEN_NOW + timedelta(days=2, minutes=5)
    assert result.session_completed is True
    assert completed_review_session.status == SessionStatus.COMPLETED
    assert completed_review_session.answered_count == 1
    assert completed_review_session.correct_count == 1
    assert review_items[0].due_at == result.due_at


def test_review_session_reschedules_incorrect_answer_with_longer_interval() -> None:
    timestamps = iter(
        (
            FROZEN_NOW,
            FROZEN_NOW + timedelta(days=1, minutes=5),
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
        ),
    )
    manager = LearningSessionManager(now=lambda: next(timestamps))
    session = manager.start_lesson(lesson)
    manager.submit_answer(session.id, "bonjour")

    review_session = manager.start_review_session(
        session.id,
        due_at=FROZEN_NOW + timedelta(days=1, minutes=1),
    )
    result = manager.submit_review_answer(review_session.id, "ciao")
    review_items = manager.get_due_review_items(
        session.id,
        due_at=FROZEN_NOW + timedelta(days=4, minutes=5),
    )

    assert result.correct is False
    assert result.incorrect_count == 2
    assert result.due_at == FROZEN_NOW + timedelta(days=4, minutes=5)
    assert review_items[0].incorrect_count == 2
    assert review_items[0].due_at == result.due_at


def test_review_session_advances_through_multiple_due_items_only() -> None:
    timestamps = iter(
        (
            FROZEN_NOW,
            FROZEN_NOW + timedelta(minutes=1),
            FROZEN_NOW + timedelta(minutes=2),
            FROZEN_NOW + timedelta(days=1, minutes=5),
            FROZEN_NOW + timedelta(days=1, minutes=6),
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
                id="thanks",
                prompt="Translate: thanks",
                correct_answers=("gracias",),
            ),
            Exercise(
                id="bye",
                prompt="Translate: goodbye",
                correct_answers=("adios",),
            ),
        ),
    )
    manager = LearningSessionManager(now=lambda: next(timestamps))
    session = manager.start_lesson(lesson)
    manager.submit_answer(session.id, "bonjour")
    manager.submit_answer(session.id, "merci")
    manager.submit_answer(session.id, "ciao")

    review_session = manager.start_review_session(
        session.id,
        due_at=FROZEN_NOW + timedelta(days=1, minutes=1),
    )

    assert review_session.review_item_ids == tuple(
        review_item.id
        for review_item in manager.get_due_review_items(
            session.id,
            due_at=FROZEN_NOW + timedelta(days=1, minutes=1),
        )
    )
    assert manager.get_current_review_exercise(review_session.id) == lesson.exercises[0]

    first_result = manager.submit_review_answer(review_session.id, "HOLA")
    in_progress_review_session = manager.get_review_session(review_session.id)

    assert first_result.correct is True
    assert first_result.due_at == FROZEN_NOW + timedelta(days=2, minutes=5)
    assert first_result.session_completed is False
    assert in_progress_review_session.status == SessionStatus.ACTIVE
    assert in_progress_review_session.current_index == 1
    assert in_progress_review_session.answered_count == 1
    assert in_progress_review_session.correct_count == 1
    assert manager.get_current_review_exercise(review_session.id) == lesson.exercises[1]

    second_result = manager.submit_review_answer(review_session.id, "wrong")
    completed_review_session = manager.get_review_session(review_session.id)
    all_review_items = manager.get_due_review_items(
        session.id,
        due_at=FROZEN_NOW + timedelta(days=4, minutes=6),
    )

    assert second_result.correct is False
    assert second_result.incorrect_count == 2
    assert second_result.due_at == FROZEN_NOW + timedelta(days=4, minutes=6)
    assert second_result.session_completed is True
    assert completed_review_session.status == SessionStatus.COMPLETED
    assert completed_review_session.answered_count == 2
    assert completed_review_session.correct_count == 1
    assert manager.get_current_review_exercise(review_session.id) is None
    assert [review_item.exercise.id for review_item in all_review_items] == [
        "bye",
        "hello",
        "thanks",
    ]
    assert all_review_items[1].incorrect_count == 1
    assert all_review_items[1].due_at == first_result.due_at
    assert all_review_items[2].incorrect_count == 2
    assert all_review_items[2].due_at == second_result.due_at


def test_review_session_uses_due_items_only_and_rejects_completed_submission() -> None:
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

    review_session = manager.start_review_session(session.id, due_at=FROZEN_NOW)

    assert review_session.status == SessionStatus.COMPLETED
    assert manager.get_current_review_exercise(review_session.id) is None
    with pytest.raises(ValueError, match="completed review session"):
        manager.submit_review_answer(review_session.id, "hola")


def test_unknown_review_session_raises_domain_error() -> None:
    manager = LearningSessionManager()

    with pytest.raises(ReviewSessionNotFoundError):
        manager.get_current_review_exercise("missing")


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
