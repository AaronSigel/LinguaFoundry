from __future__ import annotations

import importlib
import inspect
import re


def test_0002_defines_original_pack_version_column_widths() -> None:
    migration = importlib.import_module(
        "services.api.alembic.versions.0002_learning_sessions_review_state"
    )
    source = inspect.getsource(migration.upgrade)

    assert _column_widths(source, "pack_version") == [32]
    assert _column_widths(source, "language_pack_version") == [32, 32, 32]


def test_0003_is_the_pack_version_widening_step(monkeypatch) -> None:
    migration = importlib.import_module(
        "services.api.alembic.versions.0003_widen_language_pack_version_columns"
    )
    operations = _RecordingOperations()
    monkeypatch.setattr(migration, "op", operations)

    migration.upgrade()

    assert [
        (
            operation["table_name"],
            operation["column_name"],
            operation["existing_type"].length,
            operation["type_"].length,
            operation["existing_nullable"],
        )
        for operation in operations.alter_column_calls
    ] == [
        ("lessons", "pack_version", 32, 128, False),
        ("learning_sessions", "language_pack_version", 32, 128, False),
        ("attempts", "language_pack_version", 32, 128, False),
        ("review_states", "language_pack_version", 32, 128, False),
    ]


def test_0003_downgrade_restores_0002_pack_version_widths(monkeypatch) -> None:
    migration = importlib.import_module(
        "services.api.alembic.versions.0003_widen_language_pack_version_columns"
    )
    operations = _RecordingOperations()
    monkeypatch.setattr(migration, "op", operations)

    migration.downgrade()

    assert [
        (
            operation["table_name"],
            operation["column_name"],
            operation["existing_type"].length,
            operation["type_"].length,
            operation["existing_nullable"],
        )
        for operation in operations.alter_column_calls
    ] == [
        ("lessons", "pack_version", 128, 32, False),
        ("learning_sessions", "language_pack_version", 128, 32, False),
        ("attempts", "language_pack_version", 128, 32, False),
        ("review_states", "language_pack_version", 128, 32, False),
    ]


class _RecordingOperations:
    def __init__(self) -> None:
        self.alter_column_calls: list[dict[str, object]] = []

    def alter_column(self, table_name: str, column_name: str, **kwargs: object) -> None:
        self.alter_column_calls.append(
            {"table_name": table_name, "column_name": column_name, **kwargs}
        )


def _column_widths(source: str, column_name: str) -> list[int]:
    matches = re.finditer(
        rf'"{column_name}",\s+sa\.String\(length=(?P<length>\d+)\)',
        source,
    )
    return [int(match.group("length")) for match in matches]
