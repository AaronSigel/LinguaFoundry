"""Answer extraction, display, and scoring helpers shared by services."""

from __future__ import annotations


def check_answer(submitted_answer: str, accepted_answers: object) -> bool | None:
    """Return whether a submitted answer matches configured accepted answers.

    ``accepted_answers`` may be the answer payload used by API exercises or a
    direct iterable of accepted answer values.
    """

    answers = extract_accepted_answers(accepted_answers)
    if not answers:
        return None

    normalized_submission = normalize_answer(submitted_answer)
    return normalized_submission in {
        normalize_answer(str(accepted_answer)) for accepted_answer in answers
    }


def extract_accepted_answers(answer_payload: object) -> tuple[object, ...]:
    """Extract accepted answer values from known exercise answer shapes."""

    if answer_payload is None:
        return ()
    if isinstance(answer_payload, dict):
        for key in ("accepted_answers", "correct_answers", "answers"):
            value = answer_payload.get(key)
            if isinstance(value, list | tuple):
                return tuple(value)

        for key in ("answer", "text", "value"):
            value = answer_payload.get(key)
            if value is not None:
                return (value,)

        return ()
    if isinstance(answer_payload, str):
        return (answer_payload,)

    try:
        return tuple(answer_payload)
    except TypeError:
        return (answer_payload,)


def expected_answer_text(answer_payload: object) -> str:
    """Return a display-friendly accepted answer string."""

    return ", ".join(str(answer) for answer in extract_accepted_answers(answer_payload))


def normalize_answer(answer: str) -> str:
    """Normalize a learner answer for case-insensitive exact matching."""

    return " ".join(answer.casefold().strip().split())
