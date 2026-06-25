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


def test_0002_widens_alembic_version_table_before_long_revision_stamp(
    monkeypatch,
) -> None:
    migration = importlib.import_module(
        "services.api.alembic.versions.0002_learning_sessions_review_state"
    )
    operations = _RecordingOperations()
    monkeypatch.setattr(migration, "op", operations)

    migration.upgrade()

    first_call = operations.calls[0]
    assert {
        key: first_call[key]
        for key in (
            "operation",
            "table_name",
            "column_name",
            "existing_nullable",
        )
    } == {
        "operation": "alter_column",
        "table_name": "alembic_version",
        "column_name": "version_num",
        "existing_nullable": False,
    }
    assert first_call["existing_type"].length == 32
    assert first_call["type_"].length == 128
    assert first_call["existing_type"].length < len(migration.revision)
    assert first_call["type_"].length >= len(migration.revision)


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
        self.calls: list[dict[str, object]] = []
        self.alter_column_calls: list[dict[str, object]] = []

    def alter_column(self, table_name: str, column_name: str, **kwargs: object) -> None:
        call = {
            "operation": "alter_column",
            "table_name": table_name,
            "column_name": column_name,
            **kwargs,
        }
        self.calls.append(call)
        self.alter_column_calls.append(call)

    def add_column(self, table_name: str, column: object, **kwargs: object) -> None:
        self.calls.append(
            {
                "operation": "add_column",
                "table_name": table_name,
                "column": column,
                **kwargs,
            }
        )

    def create_foreign_key(self, *args: object, **kwargs: object) -> None:
        self.calls.append({"operation": "create_foreign_key", "args": args, **kwargs})

    def create_index(self, *args: object, **kwargs: object) -> None:
        self.calls.append({"operation": "create_index", "args": args, **kwargs})

    def create_table(self, table_name: str, *columns: object, **kwargs: object) -> None:
        self.calls.append(
            {
                "operation": "create_table",
                "table_name": table_name,
                "columns": columns,
                **kwargs,
            }
        )

    def create_unique_constraint(self, *args: object, **kwargs: object) -> None:
        self.calls.append(
            {"operation": "create_unique_constraint", "args": args, **kwargs}
        )

    def drop_constraint(self, *args: object, **kwargs: object) -> None:
        self.calls.append({"operation": "drop_constraint", "args": args, **kwargs})

    def f(self, name: str) -> str:
        return name


def _column_widths(source: str, column_name: str) -> list[int]:
    matches = re.finditer(
        rf'"{column_name}",\s+sa\.String\(length=(?P<length>\d+)\)',
        source,
    )
    return [int(match.group("length")) for match in matches]
