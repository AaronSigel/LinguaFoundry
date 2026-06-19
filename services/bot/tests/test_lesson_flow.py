from services.bot.lesson_catalog import LessonCatalog
from services.bot.lesson_flow import TelegramLessonFlow

from linguafoundry_core.learning import Exercise, Lesson


def test_lesson_flow_lists_lessons_and_advances_after_answers() -> None:
    flow = TelegramLessonFlow(
        LessonCatalog(
            (
                Lesson(
                    id="intro",
                    title="Intro",
                    exercises=(
                        Exercise(
                            id="hello",
                            prompt="Translate: hello",
                            correct_answers=("hola",),
                            explanation="Hola means hello.",
                        ),
                        Exercise(
                            id="bye",
                            prompt="Translate: goodbye",
                            correct_answers=("adios",),
                        ),
                    ),
                ),
            )
        )
    )

    lesson_list = flow.handle_message(chat_id=42, text="/lessons")
    started = flow.handle_message(chat_id=42, text="/lesson intro")
    first_result = flow.handle_message(chat_id=42, text="hola")
    second_result = flow.handle_message(chat_id=42, text="wrong")

    assert "/lesson intro - Intro" in lesson_list.text
    assert "Lesson started: Intro" in started.text
    assert "Exercise 1/2" in started.text
    assert "Correct." in first_result.text
    assert "Hola means hello." in first_result.text
    assert "Exercise 2/2" in first_result.text
    assert "Incorrect." in second_result.text
    assert "Expected: adios" in second_result.text
    assert "Lesson complete: 1/2 correct." in second_result.text


def test_answer_before_lesson_prompts_for_lesson_selection() -> None:
    flow = TelegramLessonFlow(
        LessonCatalog(
            (
                Lesson(
                    id="intro",
                    title="Intro",
                    exercises=(
                        Exercise(
                            id="hello",
                            prompt="Translate: hello",
                            correct_answers=("hola",),
                        ),
                    ),
                ),
            )
        )
    )

    reply = flow.handle_message(chat_id=42, text="hola")

    assert "Choose a lesson before sending an answer." in reply.text
    assert "/lesson intro - Intro" in reply.text


def test_language_pack_multiple_choice_prompt_includes_options() -> None:
    lesson = LessonCatalog.from_language_pack().get("hello-and-goodbye")
    exercise = lesson.exercises[0]

    assert exercise.prompt == (
        "Which word means hello?\n- hola\n- adios\nChoose one answer."
    )
