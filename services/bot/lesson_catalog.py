"""Load lesson content for the Telegram lesson flow."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from linguafoundry_core.learning import Exercise, Lesson

DEFAULT_LANGUAGE_PACK = (
    Path(__file__).resolve().parents[2]
    / "packages"
    / "lang-packs"
    / "examples"
    / "es-a1-greetings.json"
)


@dataclass(frozen=True, slots=True)
class LessonSummary:
    """Small display model for selectable lessons."""

    id: str
    title: str


class LessonCatalog:
    """Read-only lesson catalog backed by language-pack JSON."""

    def __init__(self, lessons: tuple[Lesson, ...]) -> None:
        if not lessons:
            raise ValueError("Lesson catalog must include at least one lesson.")
        self._lessons = {lesson.id: lesson for lesson in lessons}

    @classmethod
    def from_language_pack(cls, path: Path = DEFAULT_LANGUAGE_PACK) -> "LessonCatalog":
        with path.open(encoding="utf-8") as language_pack:
            payload = json.load(language_pack)
        return cls(_read_lessons(payload))

    def list_lessons(self) -> tuple[LessonSummary, ...]:
        return tuple(
            LessonSummary(id=lesson.id, title=lesson.title)
            for lesson in self._lessons.values()
        )

    def get(self, lesson_id: str) -> Lesson:
        try:
            return self._lessons[lesson_id]
        except KeyError as error:
            raise LessonNotFoundError(lesson_id) from error


class LessonNotFoundError(LookupError):
    """Raised when a learner selects an unknown lesson."""


def _read_lessons(payload: dict[str, Any]) -> tuple[Lesson, ...]:
    lessons: list[Lesson] = []
    for level in payload.get("levels", []):
        for topic in level.get("topics", []):
            for lesson_payload in topic.get("lessons", []):
                lessons.append(_read_lesson(lesson_payload))
    return tuple(lessons)


def _read_lesson(payload: dict[str, Any]) -> Lesson:
    exercises = sorted(payload.get("exercises", []), key=lambda item: item.get("order", 0))
    return Lesson(
        id=payload["id"],
        title=payload["title"],
        exercises=tuple(_read_exercise(exercise) for exercise in exercises),
    )


def _read_exercise(payload: dict[str, Any]) -> Exercise:
    answers = tuple(
        answer.get("normalized_value") or answer["value"]
        for answer in payload.get("answers", [])
    )
    return Exercise(
        id=payload["id"],
        prompt=_read_prompt(payload),
        correct_answers=answers,
        explanation=payload.get("explanation", {}).get("text"),
    )


def _read_prompt(payload: dict[str, Any]) -> str:
    prompt = payload.get("prompt", {})
    lines = [prompt["text"]]
    options = payload.get("options", [])
    if options:
        lines.extend(f"- {option['text']}" for option in options)
    if instruction := prompt.get("instruction"):
        lines.append(instruction)
    return "\n".join(lines)
