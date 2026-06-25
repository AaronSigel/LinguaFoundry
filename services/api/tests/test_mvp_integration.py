from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator
from pathlib import Path
from uuid import UUID

import httpx
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import func, select
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from services.api.app.config import Settings, get_settings
from services.api.app.db.database import get_session
from services.api.app.db.models import (
    Attempt,
    LearningSession,
    Lesson,
    Progress,
    ReviewState,
)
from services.api.app.lang_packs import import_language_pack, load_language_pack
from services.api.app.main import create_app

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
LANG_PACK_PATH = REPOSITORY_ROOT / "packages/lang-packs/examples/es-a1-greetings.json"


pytestmark = pytest.mark.integration


def test_pack_version_columns_allow_content_version_identifiers() -> None:
    for model, column_name in (
        (Lesson, "pack_version"),
        (LearningSession, "language_pack_version"),
        (Attempt, "language_pack_version"),
        (ReviewState, "language_pack_version"),
    ):
        assert model.__table__.c[column_name].type.length == 128


def test_mvp_learning_workflow_persists_across_application_restart(monkeypatch) -> None:
    database_url = os.getenv("TEST_DATABASE_URL")
    if database_url is None:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL integration tests.")

    _require_test_database_url(database_url)
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()
    alembic_config = Config(str(REPOSITORY_ROOT / "services/api/alembic.ini"))
    command.downgrade(alembic_config, "base")
    command.upgrade(alembic_config, "head")

    try:
        asyncio.run(_run_mvp_learning_workflow(database_url))
    finally:
        command.downgrade(alembic_config, "base")
        get_settings.cache_clear()


@pytest.mark.parametrize(
    "database_url",
    [
        "postgresql+asyncpg://user@localhost:5432/linguafoundry_test",
        "postgresql+asyncpg://user@db.example.test:5432/ci_test",
        "postgresql+asyncpg://user:password@localhost:5432/linguafoundry_test",
    ],
)
def test_integration_database_url_guard_accepts_test_databases(
    database_url: str,
) -> None:
    _require_test_database_url(database_url)


@pytest.mark.parametrize(
    "database_url",
    [
        "postgresql+asyncpg://localhost:5432/linguafoundry",
        "postgresql://localhost:5432/linguafoundry_test",
        "sqlite+aiosqlite:///tmp/linguafoundry_test.db",
        "postgresql+asyncpg://localhost:5432/postgres",
        "postgresql+asyncpg://localhost:5432/",
        "postgresql+asyncpg://localhost:5432/linguafoundry_test",
    ],
)
def test_integration_database_url_guard_rejects_unsafe_targets(
    database_url: str,
) -> None:
    with pytest.raises(ValueError, match="TEST_DATABASE_URL must target"):
        _require_test_database_url(database_url)


def _require_test_database_url(database_url: str) -> None:
    url = make_url(database_url)
    database_name = (url.database or "").lower()
    if (
        url.drivername != "postgresql+asyncpg"
        or not url.username
        or not database_name.endswith("_test")
    ):
        raise ValueError(
            "TEST_DATABASE_URL must target a PostgreSQL asyncpg database with a "
            "username and a database name ending in '_test' because this test "
            "drops and recreates schema."
        )


async def _run_mvp_learning_workflow(database_url: str) -> None:
    engine = create_async_engine(database_url)
    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    try:
        async with session_factory() as session:
            stats = await import_language_pack(
                session, load_language_pack(LANG_PACK_PATH)
            )
        assert stats.packs == 1
        assert stats.lessons_created == 1
        assert stats.exercises_created == 2

        app = create_app(Settings(app_env="test"))
        _override_database_session(app, session_factory)

        async with _client_for(app) as client:
            user_response = await client.post(
                "/learning/users",
                json={
                    "telegram_id": 1001,
                    "username": "mvp_integration",
                    "first_name": "MVP",
                    "interface_language": "en",
                },
            )
            assert user_response.status_code == 201
            user_id = user_response.json()["id"]

            lessons_response = await client.get("/learning/lessons?language_code=es")
            assert lessons_response.status_code == 200
            lessons = lessons_response.json()
            assert len(lessons) == 1
            assert lessons[0]["exercise_count"] == 2
            lesson_id = lessons[0]["id"]

            session_response = await client.post(
                "/learning/sessions",
                json={"user_id": user_id, "lesson_id": lesson_id},
            )
            assert session_response.status_code == 201
            learning_session = session_response.json()
            assert learning_session["completed_exercises"] == 0
            assert learning_session["total_exercises"] == 2
            session_id = learning_session["session_id"]
            session_uuid = UUID(session_id)

            first_exercise_response = await client.get(
                f"/learning/sessions/{session_id}/exercise"
            )
            assert first_exercise_response.status_code == 200
            first_exercise = first_exercise_response.json()["exercise"]
            assert first_exercise["slug"] == "choose-hello"

            correct_answer_response = await client.post(
                f"/learning/sessions/{session_id}/answers",
                json={"answer": "hola"},
            )
            assert correct_answer_response.status_code == 200
            correct_answer = correct_answer_response.json()
            assert correct_answer["is_correct"] is True
            assert correct_answer["session_completed"] is False
            assert correct_answer["progress"]["completed_exercises"] == 1
            correct_attempt_id = correct_answer["attempt_id"]
            correct_attempt_uuid = UUID(correct_attempt_id)
            first_exercise_id = correct_answer["exercise_id"]

            second_exercise_response = await client.get(
                f"/learning/sessions/{session_id}/exercise"
            )
            assert second_exercise_response.status_code == 200
            second_exercise = second_exercise_response.json()["exercise"]
            assert second_exercise["slug"] == "translate-goodbye"

            incorrect_answer_response = await client.post(
                f"/learning/sessions/{session_id}/answers",
                json={"answer": "__incorrect_integration_answer__"},
            )
            assert incorrect_answer_response.status_code == 200
            incorrect_answer = incorrect_answer_response.json()
            assert incorrect_answer["is_correct"] is False
            assert incorrect_answer["session_completed"] is True
            assert incorrect_answer["progress"]["completed_exercises"] == 2
            incorrect_attempt_id = incorrect_answer["attempt_id"]
            incorrect_attempt_uuid = UUID(incorrect_attempt_id)
            second_exercise_id = incorrect_answer["exercise_id"]

            progress_response = await client.get(f"/learning/users/{user_id}/progress")
            assert progress_response.status_code == 200
            progress = progress_response.json()
            assert len(progress) == 1
            assert progress[0]["status"] == "completed"
            assert progress[0]["completed_exercises"] == 2
            assert progress[0]["total_exercises"] == 2

        restarted_app = create_app(Settings(app_env="test"))
        _override_database_session(restarted_app, session_factory)

        async with _client_for(restarted_app) as restarted_client:
            completed_session_response = await restarted_client.get(
                f"/learning/sessions/{session_id}/exercise"
            )
            assert completed_session_response.status_code == 200
            completed_session = completed_session_response.json()
            assert completed_session["status"] == "completed"
            assert completed_session["exercise"] is None

            stats_response = await restarted_client.get(
                f"/learning/users/{user_id}/progress/stats"
            )
            assert stats_response.status_code == 200
            stats_payload = stats_response.json()
            assert stats_payload["answer_count"] == 2
            assert stats_payload["accuracy"] == 0.5
            assert stats_payload["accuracy_percent"] == 50.0
            assert stats_payload["completed_lessons"] == 1
            assert stats_payload["active_repetitions"] == 1
            assert stats_payload["last_activity_at"] is not None

            review_response = await restarted_client.get(
                f"/learning/users/{user_id}/review"
            )
            assert review_response.status_code == 200
            review_payload = review_response.json()
            assert len(review_payload["cards"]) == 1
            assert review_payload["cards"][0]["prompt"] == "Translate: goodbye"
            assert review_payload["cards"][0]["expected_answer"] == "adios"
            assert review_payload["cards"][0]["incorrect_attempts"] == 1

        async with session_factory() as session:
            attempts = (
                (
                    await session.execute(
                        select(Attempt).where(
                            Attempt.id.in_(
                                [correct_attempt_uuid, incorrect_attempt_uuid],
                            )
                        )
                    )
                )
                .scalars()
                .all()
            )
            attempt_count = await session.scalar(select(func.count(Attempt.id)))
            persisted_session = await session.scalar(
                select(LearningSession).where(LearningSession.id == session_uuid)
            )
            progress_record = await session.scalar(select(Progress))
            review_state = await session.scalar(select(ReviewState))

        attempts_by_id = {str(attempt.id): attempt for attempt in attempts}
        assert attempt_count == 2
        assert set(attempts_by_id) == {correct_attempt_id, incorrect_attempt_id}
        correct_attempt = attempts_by_id[correct_attempt_id]
        assert str(correct_attempt.exercise_id) == first_exercise_id
        assert str(correct_attempt.learning_session_id) == session_id
        assert correct_attempt.answer == {"answer": "hola"}
        assert correct_attempt.is_correct is True
        assert str(correct_attempt.score) == "1.00"
        incorrect_attempt = attempts_by_id[incorrect_attempt_id]
        assert str(incorrect_attempt.exercise_id) == second_exercise_id
        assert str(incorrect_attempt.learning_session_id) == session_id
        assert incorrect_attempt.answer == {
            "answer": "__incorrect_integration_answer__"
        }
        assert incorrect_attempt.is_correct is False
        assert str(incorrect_attempt.score) == "0.00"
        assert persisted_session is not None
        assert persisted_session.status == "completed"
        assert persisted_session.current_exercise_index == 2
        assert persisted_session.completed_at is not None
        assert progress_record is not None
        assert progress_record.status == "completed"
        assert progress_record.completed_exercises == 2
        assert review_state is not None
        assert review_state.status == "active"
        assert review_state.incorrect_count == 1
        assert str(review_state.last_attempt_id) == incorrect_attempt_id
        assert str(review_state.learning_session_id) == session_id
        assert str(review_state.exercise_id) == second_exercise_id
        assert review_state.due_at > incorrect_attempt.attempted_at
    finally:
        await engine.dispose()


def _override_database_session(app, session_factory) -> None:
    async def override_get_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session


def _client_for(app) -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://testserver")
