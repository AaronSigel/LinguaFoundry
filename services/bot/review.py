"""Telegram review command rendering."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from linguafoundry_core import Attempt, Exercise, ReviewCard, build_mistake_review_queue

REVIEW_COMMAND = "/review"
REVIEW_COMMAND_ALIASES = frozenset({REVIEW_COMMAND, "/mistakes", "/repeat_errors"})


@dataclass(frozen=True, slots=True)
class ReviewCommandResponse:
    """Telegram-ready response for a review command."""

    text: str
    cards: tuple[ReviewCard, ...]


def is_review_command(message_text: str) -> bool:
    """Return whether a Telegram message requests mistake review."""

    command = message_text.strip().split(maxsplit=1)[0].casefold()
    command = command.split("@", maxsplit=1)[0]
    return command in REVIEW_COMMAND_ALIASES


def render_review_command_response(
    *,
    user_id: str,
    attempts: Iterable[Attempt],
    exercises: Iterable[Exercise],
    limit: int = 5,
) -> ReviewCommandResponse:
    """Build Telegram text for the learner's due mistake reviews."""

    cards = build_mistake_review_queue(
        attempts=attempts,
        exercises=exercises,
        user_id=user_id,
        limit=limit,
    )
    if not cards:
        return ReviewCommandResponse(
            text="No mistakes to review yet. Missed exercises will appear here.",
            cards=cards,
        )

    lines = ["Review your missed exercises:"]
    for index, card in enumerate(cards, start=1):
        lines.append(f"{index}. {card.prompt}")
        lines.append(f"Answer: {card.expected_answer}")

    return ReviewCommandResponse(text="\n".join(lines), cards=cards)
