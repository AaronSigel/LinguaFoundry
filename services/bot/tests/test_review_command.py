from datetime import datetime, timezone

from linguafoundry_core import Attempt, AttemptResult, Exercise, ExerciseType
from services.bot.review import (
    is_review_command,
    render_review_command_response,
)


def test_review_command_aliases_include_telegram_mentions() -> None:
    assert is_review_command("/review")
    assert is_review_command("/review@LinguaFoundryBot")
    assert is_review_command("/repeat_errors")
    assert not is_review_command("/start")


def test_render_review_command_response_lists_due_mistakes() -> None:
    response = render_review_command_response(
        user_id="user-1",
        exercises=(
            Exercise(
                id="hello",
                lesson_id="lesson-1",
                exercise_type=ExerciseType.TEXT_INPUT,
                prompt="Translate: hello",
                expected_answer="hola",
            ),
        ),
        attempts=(
            Attempt(
                id="attempt-1",
                user_id="user-1",
                exercise_id="hello",
                submitted_answer="ola",
                result=AttemptResult.INCORRECT,
                attempted_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            ),
        ),
    )

    assert response.cards[0].exercise_id == "hello"
    assert (
        response.text
        == "Review your missed exercises:\n1. Translate: hello\nAnswer: hola"
    )


def test_render_review_command_response_handles_empty_queue() -> None:
    response = render_review_command_response(
        user_id="user-1",
        exercises=(),
        attempts=(),
    )

    assert response.cards == ()
    assert (
        response.text == "No mistakes to review yet. Missed exercises will appear here."
    )
