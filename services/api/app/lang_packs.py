"""Language pack validation and database import helpers."""

from __future__ import annotations

import argparse
import asyncio
import json
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.api.app.db.database import async_session_factory
from services.api.app.db.models import Exercise, Lesson

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
LANG_PACKS_ROOT = REPOSITORY_ROOT / "packages" / "lang-packs"
LANG_PACK_SCHEMA_PATH = LANG_PACKS_ROOT / "schema" / "language-pack.schema.json"
DEFAULT_LANG_PACKS_PATH = LANG_PACKS_ROOT / "examples"
MAX_DATABASE_SLUG_LENGTH = 128

JsonObject = dict[str, Any]


class LanguagePackError(ValueError):
    """Raised when a language pack cannot be loaded or validated."""


@dataclass(frozen=True)
class ExerciseImportRecord:
    """Database-ready exercise content from a language pack."""

    stable_id: str
    slug: str
    kind: str
    prompt: str
    payload: JsonObject
    answer: JsonObject
    position: int


@dataclass(frozen=True)
class LessonImportRecord:
    """Database-ready lesson content from a language pack."""

    stable_id: str
    language_code: str
    pack_id: str
    pack_version: str
    title: str
    description: str | None
    level: str
    position: int
    exercises: tuple[ExerciseImportRecord, ...]


@dataclass(frozen=True)
class ImportStats:
    """Summary of a language-pack import run."""

    packs: int = 0
    lessons_created: int = 0
    lessons_updated: int = 0
    exercises_created: int = 0
    exercises_updated: int = 0

    def __add__(self, other: ImportStats) -> ImportStats:
        return ImportStats(
            packs=self.packs + other.packs,
            lessons_created=self.lessons_created + other.lessons_created,
            lessons_updated=self.lessons_updated + other.lessons_updated,
            exercises_created=self.exercises_created + other.exercises_created,
            exercises_updated=self.exercises_updated + other.exercises_updated,
        )


def discover_language_pack_files(paths: Sequence[Path]) -> list[Path]:
    """Return sorted JSON files from explicit files or directories."""

    files: list[Path] = []
    for path in paths:
        if path.is_dir():
            files.extend(path.glob("*.json"))
        else:
            files.append(path)
    return sorted({file.resolve() for file in files})


def load_language_pack(path: Path) -> JsonObject:
    """Load and validate a language pack JSON file."""

    try:
        pack = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise LanguagePackError(f"{path}: invalid JSON: {exc}") from exc

    if not isinstance(pack, dict):
        raise LanguagePackError(f"{path}: language pack must be a JSON object")

    validate_language_pack(pack, source=path)
    return pack


def validate_language_pack(pack: JsonObject, *, source: Path | None = None) -> None:
    """Validate a language pack against schema and stable-ID constraints."""

    schema = json.loads(LANG_PACK_SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(pack), key=_validation_error_sort_key)
    if errors:
        first_error = errors[0]
        location = "/".join(str(item) for item in first_error.absolute_path) or "."
        raise LanguagePackError(
            f"{_source_label(source)}{location}: {first_error.message}"
        ) from first_error

    duplicate = _first_duplicate(_stable_ids_for_pack(pack))
    if duplicate is not None:
        raise LanguagePackError(
            f"{_source_label(source)}duplicate stable identifier: {duplicate}"
        )

    _validate_database_identifier_lengths(pack, source=source)


def validate_language_pack_files(paths: Sequence[Path]) -> list[Path]:
    """Validate all discovered language pack files and return their paths."""

    files = discover_language_pack_files(paths)
    seen_pack_ids: set[str] = set()
    for file in files:
        pack = load_language_pack(file)
        pack_id = str(pack["pack_id"])
        if pack_id in seen_pack_ids:
            raise LanguagePackError(
                f"{file}: duplicate pack_id across files: {pack_id}"
            )
        seen_pack_ids.add(pack_id)
    return files


def build_lesson_records(pack: JsonObject) -> tuple[LessonImportRecord, ...]:
    """Project a validated language pack into database import records."""

    language_code = str(pack["language"]["code"])
    pack_id = str(pack["pack_id"])
    lessons: list[LessonImportRecord] = []
    for level in pack["levels"]:
        level_id = str(level["id"])
        for topic in level["topics"]:
            topic_id = str(topic["id"])
            for lesson in topic["lessons"]:
                lesson_id = str(lesson["id"])
                stable_lesson_id = stable_lesson_id_for(
                    pack_id=pack_id,
                    level_id=level_id,
                    topic_id=topic_id,
                    lesson_id=lesson_id,
                )
                exercises = tuple(
                    _exercise_record(
                        exercise,
                        pack=pack,
                        level=level,
                        topic=topic,
                        lesson=lesson,
                        lesson_stable_id=stable_lesson_id,
                    )
                    for exercise in lesson["exercises"]
                )
                lessons.append(
                    LessonImportRecord(
                        stable_id=stable_lesson_id,
                        language_code=language_code,
                        pack_id=pack_id,
                        pack_version=str(pack["schema_version"]),
                        title=str(lesson["title"]),
                        description=lesson.get("description"),
                        level=level_id,
                        position=_ordered_position(level, topic, lesson),
                        exercises=exercises,
                    )
                )
    return tuple(sorted(lessons, key=lambda item: (item.position, item.stable_id)))


def stable_lesson_id_for(
    *,
    pack_id: str,
    level_id: str,
    topic_id: str,
    lesson_id: str,
) -> str:
    """Return the stable database slug for a lesson."""

    return "-".join((pack_id, level_id.casefold(), topic_id, lesson_id))


async def import_language_pack(session: AsyncSession, pack: JsonObject) -> ImportStats:
    """Import one validated language pack into lessons and exercises."""

    validate_language_pack(pack)
    stats = ImportStats(packs=1)
    for record in build_lesson_records(pack):
        lesson = await session.scalar(
            select(Lesson).where(
                Lesson.pack_id == record.pack_id,
                Lesson.pack_version == record.pack_version,
                Lesson.slug == record.stable_id,
            )
        )
        if lesson is None:
            lesson = Lesson(
                language_code=record.language_code,
                pack_id=record.pack_id,
                pack_version=record.pack_version,
                slug=record.stable_id,
            )
            session.add(lesson)
            stats += ImportStats(lessons_created=1)
        else:
            stats += ImportStats(lessons_updated=1)

        lesson.title = record.title
        lesson.language_code = record.language_code
        lesson.pack_id = record.pack_id
        lesson.pack_version = record.pack_version
        lesson.description = record.description
        lesson.level = record.level
        lesson.position = record.position
        lesson.is_published = True

        if lesson.id is None:
            await session.flush()

        for exercise_record in record.exercises:
            exercise = await session.scalar(
                select(Exercise).where(
                    Exercise.lesson_id == lesson.id,
                    Exercise.slug == exercise_record.slug,
                )
            )
            if exercise is None:
                exercise = Exercise(lesson_id=lesson.id, slug=exercise_record.slug)
                session.add(exercise)
                stats += ImportStats(exercises_created=1)
            else:
                stats += ImportStats(exercises_updated=1)

            exercise.kind = exercise_record.kind
            exercise.prompt = exercise_record.prompt
            exercise.payload = exercise_record.payload
            exercise.answer = exercise_record.answer
            exercise.position = exercise_record.position

    await session.commit()
    return stats


async def import_language_pack_files(paths: Sequence[Path]) -> ImportStats:
    """Import all language pack files from explicit files or directories."""

    files = validate_language_pack_files(paths)
    stats = ImportStats()
    async with async_session_factory() as session:
        for file in files:
            stats += await import_language_pack(session, load_language_pack(file))
    return stats


def _exercise_record(
    exercise: JsonObject,
    *,
    pack: JsonObject,
    level: JsonObject,
    topic: JsonObject,
    lesson: JsonObject,
    lesson_stable_id: str,
) -> ExerciseImportRecord:
    exercise_id = str(exercise["id"])
    stable_exercise_id = f"{lesson_stable_id}-{exercise_id}"
    accepted_answers = [
        str(answer.get("normalized_value") or answer["value"])
        for answer in exercise["answers"]
    ]
    prompt = exercise["prompt"]
    payload = {
        "stable_id": stable_exercise_id,
        "pack_id": pack["pack_id"],
        "level_id": level["id"],
        "topic_id": topic["id"],
        "lesson_id": lesson["id"],
        "exercise_id": exercise_id,
        "prompt": prompt,
        "options": exercise.get("options", []),
        "explanation": exercise["explanation"],
        "tags": exercise.get("tags", []),
        "learning_objectives": lesson.get("learning_objectives", []),
        "vocabulary": lesson.get("vocabulary", []),
    }
    answer = {
        "accepted_answers": accepted_answers,
        "answers": exercise["answers"],
        "explanation": exercise["explanation"],
    }
    return ExerciseImportRecord(
        stable_id=stable_exercise_id,
        slug=exercise_id,
        kind=str(exercise["type"]),
        prompt=str(prompt["text"]),
        payload=payload,
        answer=answer,
        position=int(exercise["order"]),
    )


def _ordered_position(level: JsonObject, topic: JsonObject, lesson: JsonObject) -> int:
    return (
        int(level["order"]) * 10_000 + int(topic["order"]) * 100 + int(lesson["order"])
    )


def _stable_ids_for_pack(pack: JsonObject) -> Iterable[str]:
    pack_id = str(pack["pack_id"])
    yield f"pack:{pack_id}"
    for lesson in build_lesson_records(pack):
        yield f"lesson:{lesson.stable_id}"
        for exercise in lesson.exercises:
            yield f"exercise:{exercise.stable_id}"


def _validate_database_identifier_lengths(
    pack: JsonObject,
    *,
    source: Path | None,
) -> None:
    for lesson in build_lesson_records(pack):
        if len(lesson.stable_id) > MAX_DATABASE_SLUG_LENGTH:
            raise LanguagePackError(
                f"{_source_label(source)}lesson stable identifier exceeds "
                f"{MAX_DATABASE_SLUG_LENGTH} characters: {lesson.stable_id}"
            )
        for exercise in lesson.exercises:
            if len(exercise.slug) > MAX_DATABASE_SLUG_LENGTH:
                raise LanguagePackError(
                    f"{_source_label(source)}exercise identifier exceeds "
                    f"{MAX_DATABASE_SLUG_LENGTH} characters: {exercise.slug}"
                )


def _first_duplicate(values: Iterable[str]) -> str | None:
    seen: set[str] = set()
    for value in values:
        if value in seen:
            return value
        seen.add(value)
    return None


def _source_label(source: Path | None) -> str:
    return f"{source}: " if source is not None else ""


def _validation_error_sort_key(error: ValidationError) -> tuple[str, str]:
    return ("/".join(str(item) for item in error.absolute_path), error.message)


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import LinguaFoundry language packs.")
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=[DEFAULT_LANG_PACKS_PATH],
        help="Language pack JSON files or directories. Defaults to example packs.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate packs without importing them into the database.",
    )
    return parser.parse_args(argv)


async def _main_async(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    files = validate_language_pack_files(args.paths)
    if args.check:
        print(f"Validated {len(files)} language pack file(s).")
        return 0

    stats = await import_language_pack_files(args.paths)
    print(
        "Imported "
        f"{stats.packs} pack(s), "
        f"{stats.lessons_created} lesson(s) created, "
        f"{stats.lessons_updated} lesson(s) updated, "
        f"{stats.exercises_created} exercise(s) created, "
        f"{stats.exercises_updated} exercise(s) updated."
    )
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entrypoint for language-pack validation and import."""

    try:
        return asyncio.run(_main_async(argv))
    except LanguagePackError as exc:
        print(f"Language pack error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
