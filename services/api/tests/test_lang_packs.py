from __future__ import annotations

import asyncio
import copy
import json
import uuid
from collections.abc import Sequence

import pytest

from services.api.app.db.models import Lesson
from services.api.app.lang_packs import (
    DEFAULT_LANG_PACKS_PATH,
    LanguagePackError,
    build_lesson_records,
    import_language_pack,
    load_language_pack,
    stable_lesson_id_for,
    validate_language_pack,
    validate_language_pack_files,
)


class _QueuedAsyncSession:
    def __init__(self, scalars: Sequence[object | None] = ()) -> None:
        self._scalars = list(scalars)
        self.added: list[object] = []
        self.commits = 0
        self.flushes = 0

    async def scalar(self, statement: object) -> object | None:
        assert self._scalars, f"unexpected scalar query: {statement}"
        return self._scalars.pop(0)

    def add(self, instance: object) -> None:
        self.added.append(instance)

    async def flush(self) -> None:
        self.flushes += 1
        for instance in self.added:
            if isinstance(instance, Lesson) and instance.id is None:
                instance.id = uuid.uuid4()

    async def commit(self) -> None:
        self.commits += 1


def test_example_language_packs_match_json_schema() -> None:
    files = validate_language_pack_files([DEFAULT_LANG_PACKS_PATH])

    assert {file.name for file in files} == {
        "es-a1-greetings.json",
        "fr-a1-seed.json",
    }


def test_build_lesson_records_defines_stable_identifiers() -> None:
    pack = load_language_pack(DEFAULT_LANG_PACKS_PATH / "es-a1-greetings.json")

    lessons = build_lesson_records(pack)

    assert len(lessons) == 1
    assert lessons[0].stable_id == "es-a1-greetings-a1-greetings-hello-and-goodbye"
    assert lessons[0].pack_id == "es-a1-greetings"
    assert lessons[0].pack_version == "1.0"
    assert lessons[0].stable_id == stable_lesson_id_for(
        pack_id="es-a1-greetings",
        level_id="A1",
        topic_id="greetings",
        lesson_id="hello-and-goodbye",
    )
    assert lessons[0].language_code == "es"
    assert lessons[0].position == 0
    assert [exercise.slug for exercise in lessons[0].exercises] == [
        "choose-hello",
        "translate-goodbye",
    ]
    assert (
        lessons[0].exercises[0].stable_id
        == "es-a1-greetings-a1-greetings-hello-and-goodbye-choose-hello"
    )
    assert lessons[0].exercises[0].answer["accepted_answers"] == ["hola"]


def test_validate_language_pack_rejects_duplicate_stable_exercise_ids() -> None:
    pack = load_language_pack(DEFAULT_LANG_PACKS_PATH / "es-a1-greetings.json")
    duplicate_pack = copy.deepcopy(pack)
    exercises = duplicate_pack["levels"][0]["topics"][0]["lessons"][0]["exercises"]
    exercises[1]["id"] = exercises[0]["id"]

    with pytest.raises(LanguagePackError, match="duplicate stable identifier"):
        validate_language_pack(duplicate_pack)


def test_validate_language_pack_files_rejects_duplicate_pack_ids(tmp_path) -> None:
    pack = load_language_pack(DEFAULT_LANG_PACKS_PATH / "es-a1-greetings.json")
    first_file = tmp_path / "first.json"
    second_file = tmp_path / "second.json"
    first_file.write_text(json.dumps(pack), encoding="utf-8")
    second_file.write_text(json.dumps(pack), encoding="utf-8")

    with pytest.raises(LanguagePackError, match="duplicate pack_id across files"):
        validate_language_pack_files([first_file, second_file])


def test_import_language_pack_creates_then_updates_existing_records() -> None:
    pack = load_language_pack(DEFAULT_LANG_PACKS_PATH / "es-a1-greetings.json")
    create_session = _QueuedAsyncSession([None, None, None])

    create_stats = asyncio.run(import_language_pack(create_session, pack))

    assert create_stats.packs == 1
    assert create_stats.lessons_created == 1
    assert create_stats.lessons_updated == 0
    assert create_stats.exercises_created == 2
    assert create_stats.exercises_updated == 0
    assert create_session.commits == 1

    lesson, first_exercise, second_exercise = create_session.added
    updated_pack = copy.deepcopy(pack)
    updated_pack["levels"][0]["topics"][0]["lessons"][0]["title"] = "Updated greeting"
    updated_pack["levels"][0]["topics"][0]["lessons"][0]["exercises"][0]["prompt"][
        "text"
    ] = "Updated prompt?"
    update_session = _QueuedAsyncSession([lesson, first_exercise, second_exercise])

    update_stats = asyncio.run(import_language_pack(update_session, updated_pack))

    assert update_stats.packs == 1
    assert update_stats.lessons_created == 0
    assert update_stats.lessons_updated == 1
    assert update_stats.exercises_created == 0
    assert update_stats.exercises_updated == 2
    assert update_session.added == []
    assert update_session.commits == 1
    assert lesson.title == "Updated greeting"
    assert lesson.pack_id == "es-a1-greetings"
    assert lesson.pack_version == "1.0"
    assert first_exercise.prompt == "Updated prompt?"
