import asyncio
import uuid
from collections.abc import Sequence
from datetime import datetime, timedelta, timezone

from services.api.app.config import Settings
from services.api.app.db.models import (
    Attempt,
    Exercise,
    LearningSession,
    Lesson,
    Progress,
    ReviewState,
    User,
)
from services.api.app.main import create_app
from services.api.app.routers.learning import (
    StartSessionRequest,
    SubmitAnswerRequest,
    _accuracy,
    _expected_answer_text,
    _latest_datetime,
    _score_answer,
    _score_value,
    get_progress_stats,
    get_review_queue,
    start_session,
    submit_answer,
)


class _ScalarResult:
    def __init__(self, value: object | None) -> None:
        self.value = value

    def scalar_one_or_none(self) -> object | None:
        return self.value

    def all(self) -> object | None:
        return self.value

    def one(self) -> object | None:
        return self.value


class _QueuedAsyncSession:
    def __init__(
        self,
        *,
        execute_scalars: Sequence[object | None] = (),
        scalar_values: Sequence[object | None] = (),
    ) -> None:
        self._execute_scalars = list(execute_scalars)
        self._scalar_values = list(scalar_values)
        self.added: list[object] = []
        self.commits = 0
        self.execute_statements: list[object] = []
        self.flushes = 0
        self.refreshed: list[object] = []
        self.scalar_statements: list[object] = []

    async def execute(self, statement: object) -> _ScalarResult:
        self.execute_statements.append(statement)
        assert self._execute_scalars, f"unexpected execute query: {statement}"
        return _ScalarResult(self._execute_scalars.pop(0))

    async def scalar(self, statement: object) -> object | None:
        self.scalar_statements.append(statement)
        assert self._scalar_values, f"unexpected scalar query: {statement}"
        return self._scalar_values.pop(0)

    def add(self, instance: object) -> None:
        self.added.append(instance)

    async def flush(self) -> None:
        self.flushes += 1
        for instance in self.added:
            if isinstance(instance, Attempt) and instance.id is None:
                instance.id = uuid.uuid4()
            if isinstance(instance, ReviewState) and instance.id is None:
                instance.id = uuid.uuid4()

    async def commit(self) -> None:
        self.commits += 1

    async def refresh(self, instance: object) -> None:
        self.refreshed.append(instance)


def test_openapi_schema_includes_learning_endpoints() -> None:
    app = create_app(Settings(app_env="test"))

    schema = app.openapi()

    assert "/learning/users" in schema["paths"]
    assert "/learning/lessons" in schema["paths"]
    assert "/learning/sessions" in schema["paths"]
    assert "/learning/sessions/{session_id}/exercise" in schema["paths"]
    assert "/learning/sessions/{session_id}/answers" in schema["paths"]
    assert "/learning/users/{user_id}/sessions/active" in schema["paths"]
    assert "/learning/users/{user_id}/progress" in schema["paths"]
    assert "/learning/users/{user_id}/progress/stats" in schema["paths"]
    assert "/learning/users/{user_id}/review" in schema["paths"]


def test_score_answer_accepts_normalized_answer_variants() -> None:
    expected_answer = {"accepted_answers": ["Buenos dias", "Buen dia"]}

    assert _score_answer("  buenos   DIAS ", expected_answer) is True
    assert _score_answer("hola", expected_answer) is False


def test_score_answer_returns_none_without_answer_key() -> None:
    assert _score_answer("hola", None) is None
    assert _score_value(None) is None


def test_expected_answer_text_uses_accepted_answers() -> None:
    assert (
        _expected_answer_text({"accepted_answers": ["hola", "buenas"]})
        == "hola, buenas"
    )
    assert _expected_answer_text(None) == ""


def test_progress_stats_helpers_handle_empty_and_latest_values() -> None:
    earlier = datetime(2026, 1, 1, 9, tzinfo=timezone.utc)
    later = datetime(2026, 1, 2, 10, tzinfo=timezone.utc)

    assert _accuracy(0, 0) == 0.0
    assert _accuracy(2, 4) == 0.5
    assert _latest_datetime(None, earlier, later) == later
    assert _latest_datetime(None, None) is None


def test_session_response_exposes_pack_version_cursor_fields() -> None:
    app = create_app(Settings(app_env="test"))

    schema = app.openapi()
    session_properties = schema["components"]["schemas"]["SessionResponse"][
        "properties"
    ]

    assert {
        "session_id",
        "completed_exercises",
        "total_exercises",
        "language_pack_id",
        "language_pack_version",
    }.issubset(session_properties)


def test_start_session_reuses_active_pack_version_cursor() -> None:
    user_id = uuid.uuid4()
    lesson_id = uuid.uuid4()
    session_id = uuid.uuid4()
    user = User(id=user_id, telegram_id=123)
    lesson = Lesson(
        id=lesson_id,
        language_code="es",
        pack_id="es-a1-greetings",
        pack_version="1.0",
        slug="es-a1-greetings-a1-greetings-hello-and-goodbye",
        title="Hello and goodbye",
        is_published=True,
    )
    progress = Progress(
        user_id=user_id,
        lesson_id=lesson_id,
        status="in_progress",
        completed_exercises=1,
        total_exercises=2,
    )
    active_session = LearningSession(
        id=session_id,
        user_id=user_id,
        lesson_id=lesson_id,
        language_pack_id=lesson.pack_id,
        language_pack_version=lesson.pack_version,
        current_exercise_index=1,
        status="in_progress",
    )
    db_session = _QueuedAsyncSession(
        execute_scalars=(user, lesson, progress, active_session),
        scalar_values=(2,),
    )

    response = asyncio.run(
        start_session(
            StartSessionRequest(user_id=user_id, lesson_id=lesson_id),
            db_session,
        )
    )

    assert response.session_id == session_id
    assert response.completed_exercises == 1
    assert response.total_exercises == 2
    assert response.language_pack_id == "es-a1-greetings"
    assert response.language_pack_version == "1.0"
    assert db_session.added == []
    assert db_session.commits == 1
    assert active_session in db_session.refreshed


def test_submit_answer_persists_attempt_and_review_state_with_pack_version() -> None:
    user_id = uuid.uuid4()
    lesson_id = uuid.uuid4()
    exercise_id = uuid.uuid4()
    session_id = uuid.uuid4()
    learning_session = LearningSession(
        id=session_id,
        user_id=user_id,
        lesson_id=lesson_id,
        language_pack_id="es-a1-greetings",
        language_pack_version="1.0",
        current_exercise_index=0,
        status="in_progress",
    )
    exercise = Exercise(
        id=exercise_id,
        lesson_id=lesson_id,
        slug="translate-goodbye",
        kind="text_input",
        prompt="Translate: goodbye",
        payload={},
        answer={"accepted_answers": ["adios"]},
        position=1,
    )
    progress = Progress(
        user_id=user_id,
        lesson_id=lesson_id,
        status="in_progress",
        completed_exercises=0,
        total_exercises=2,
    )
    db_session = _QueuedAsyncSession(
        execute_scalars=(learning_session, exercise, progress, None),
        scalar_values=(2,),
    )

    response = asyncio.run(
        submit_answer(
            session_id,
            SubmitAnswerRequest(answer="hola"),
            db_session,
        )
    )

    attempt = next(item for item in db_session.added if isinstance(item, Attempt))
    review_state = next(
        item for item in db_session.added if isinstance(item, ReviewState)
    )
    assert response.exercise_id == exercise_id
    assert response.is_correct is False
    assert response.session_completed is False
    assert response.progress.completed_exercises == 1
    assert response.progress.language_pack_id == "es-a1-greetings"
    assert attempt.user_id == user_id
    assert attempt.exercise_id == exercise_id
    assert attempt.learning_session_id == session_id
    assert attempt.language_pack_id == "es-a1-greetings"
    assert attempt.language_pack_version == "1.0"
    assert attempt.answer == {"answer": "hola"}
    assert attempt.is_correct is False
    assert review_state.user_id == user_id
    assert review_state.lesson_id == lesson_id
    assert review_state.exercise_id == exercise_id
    assert review_state.learning_session_id == session_id
    assert review_state.language_pack_id == "es-a1-greetings"
    assert review_state.language_pack_version == "1.0"
    assert review_state.last_attempt_id == attempt.id
    assert review_state.due_at > learning_session.last_seen_at
    assert learning_session.current_exercise_index == 1
    assert progress.completed_exercises == 1
    assert db_session.flushes == 1
    assert db_session.commits == 1


def test_review_queue_returns_active_mistakes_before_due_date() -> None:
    user_id = uuid.uuid4()
    lesson_id = uuid.uuid4()
    exercise_id = uuid.uuid4()
    session_id = uuid.uuid4()
    now = datetime(2026, 1, 2, 10, 30, tzinfo=timezone.utc)
    user = User(id=user_id, telegram_id=123)
    exercise = Exercise(
        id=exercise_id,
        lesson_id=lesson_id,
        slug="translate-goodbye",
        kind="text_input",
        prompt="Translate: goodbye",
        payload={},
        answer={"accepted_answers": ["adios"]},
        position=1,
    )
    review_state = ReviewState(
        user_id=user_id,
        lesson_id=lesson_id,
        exercise_id=exercise_id,
        learning_session_id=session_id,
        language_pack_id="es-a1-greetings",
        language_pack_version="1.0",
        status="active",
        incorrect_count=1,
        due_at=now + timedelta(days=1),
        updated_at=now,
    )
    db_session = _QueuedAsyncSession(
        execute_scalars=(user, [(review_state, exercise)]),
    )

    response = asyncio.run(get_review_queue(user_id, db_session))

    assert response.user_id == user_id
    assert len(response.cards) == 1
    assert response.cards[0].exercise_id == exercise_id
    assert response.cards[0].prompt == "Translate: goodbye"
    assert response.cards[0].expected_answer == "adios"
    assert response.cards[0].incorrect_attempts == 1
    assert response.cards[0].last_attempted_at == now
    review_query = str(db_session.execute_statements[-1])
    assert "review_states.status" in review_query
    assert "review_states.due_at <=" not in review_query


def test_progress_stats_counts_active_mistakes_before_due_date() -> None:
    user_id = uuid.uuid4()
    user = User(id=user_id, telegram_id=123)
    now = datetime(2026, 1, 2, 10, 30, tzinfo=timezone.utc)
    db_session = _QueuedAsyncSession(
        execute_scalars=(user, (1, 0)),
        scalar_values=(
            now,
            0,
            1,
            now - timedelta(minutes=5),
            now,
        ),
    )

    response = asyncio.run(get_progress_stats(user_id, db_session))

    assert response.user_id == user_id
    assert response.answer_count == 1
    assert response.accuracy == 0.0
    assert response.completed_lessons == 0
    assert response.active_repetitions == 1
    assert response.last_activity_at == now
    active_repetition_query = next(
        str(statement)
        for statement in db_session.scalar_statements
        if "review_states" in str(statement)
    )
    assert "review_states.status" in active_repetition_query
    assert "review_states.due_at <=" not in active_repetition_query
