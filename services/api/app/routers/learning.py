"""Learning workflow endpoints."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Annotated, TypeVar
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from services.api.app.db.database import get_session
from services.api.app.db.models import (
    Attempt,
    Exercise,
    LearningSession,
    Lesson,
    Progress,
    ReviewState,
    User,
)

REVIEW_INTERVAL_DAYS = (1, 3, 7, 14)

router = APIRouter(prefix="/learning", tags=["learning"])
ModelT = TypeVar("ModelT")


class UserCreateRequest(BaseModel):
    """Payload for registering or updating a learner."""

    telegram_id: int | None = None
    username: str | None = Field(default=None, max_length=64)
    first_name: str | None = Field(default=None, max_length=128)
    last_name: str | None = Field(default=None, max_length=128)
    interface_language: str | None = Field(default=None, max_length=16)


class UserResponse(BaseModel):
    """Learner response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    telegram_id: int | None
    username: str | None
    first_name: str | None
    last_name: str | None
    interface_language: str | None


class LessonResponse(BaseModel):
    """Published lesson summary."""

    id: UUID
    language_code: str
    slug: str
    title: str
    description: str | None
    level: str | None
    position: int
    exercise_count: int


class StartSessionRequest(BaseModel):
    """Payload for starting a learning session."""

    user_id: UUID
    lesson_id: UUID


class SessionResponse(BaseModel):
    """Learning session state backed by a durable session row."""

    session_id: UUID
    user_id: UUID
    lesson_id: UUID
    status: str
    completed_exercises: int
    total_exercises: int
    language_pack_id: str
    language_pack_version: str


class ExerciseResponse(BaseModel):
    """Exercise payload exposed to learners."""

    id: UUID
    slug: str
    kind: str
    prompt: str
    payload: dict[str, object]
    position: int


class CurrentExerciseResponse(BaseModel):
    """Current session exercise, or no exercise when complete."""

    session_id: UUID
    status: str
    exercise: ExerciseResponse | None


class SubmitAnswerRequest(BaseModel):
    """Learner answer submission."""

    answer: str


class SubmitAnswerResponse(BaseModel):
    """Result of a learner answer submission."""

    attempt_id: UUID
    exercise_id: UUID
    is_correct: bool | None
    session_completed: bool
    progress: SessionResponse


class ProgressResponse(BaseModel):
    """Per-lesson progress for a learner."""

    id: UUID
    user_id: UUID
    lesson_id: UUID
    lesson_title: str
    status: str
    completed_exercises: int
    total_exercises: int
    last_attempt_at: datetime | None
    completed_at: datetime | None


class ProgressStatsResponse(BaseModel):
    """Aggregate progress statistics for a learner."""

    user_id: UUID
    answer_count: int
    accuracy: float
    accuracy_percent: float
    completed_lessons: int
    active_repetitions: int
    last_activity_at: datetime | None


class ReviewCardResponse(BaseModel):
    """Exercise selected for mistake review."""

    exercise_id: UUID
    prompt: str
    expected_answer: str
    incorrect_attempts: int
    last_attempted_at: datetime


class ReviewQueueResponse(BaseModel):
    """Mistake review queue for a learner."""

    user_id: UUID
    cards: list[ReviewCardResponse]


@router.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_user(
    payload: UserCreateRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> User:
    """Register a learner, updating an existing Telegram user when present."""

    user: User | None = None
    if payload.telegram_id is not None:
        user = await _scalar_or_none(
            session,
            select(User).where(User.telegram_id == payload.telegram_id),
        )

    if user is None:
        user = User(**payload.model_dump())
        session.add(user)
    else:
        for field, value in payload.model_dump().items():
            setattr(user, field, value)

    await session.commit()
    await session.refresh(user)
    return user


@router.get("/lessons", response_model=list[LessonResponse])
async def list_lessons(
    session: Annotated[AsyncSession, Depends(get_session)],
    language_code: str | None = None,
) -> list[LessonResponse]:
    """Return published lessons, optionally filtered by language."""

    exercise_count = (
        select(func.count(Exercise.id))
        .where(Exercise.lesson_id == Lesson.id)
        .correlate(Lesson)
        .scalar_subquery()
    )
    statement = select(Lesson, exercise_count.label("exercise_count")).where(
        Lesson.is_published.is_(True)
    )
    if language_code is not None:
        statement = statement.where(Lesson.language_code == language_code)
    statement = statement.order_by(Lesson.language_code, Lesson.position, Lesson.title)

    rows = (await session.execute(statement)).all()
    return [
        LessonResponse(
            id=lesson.id,
            language_code=lesson.language_code,
            slug=lesson.slug,
            title=lesson.title,
            description=lesson.description,
            level=lesson.level,
            position=lesson.position,
            exercise_count=exercise_total,
        )
        for lesson, exercise_total in rows
    ]


@router.post(
    "/sessions",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_session(
    payload: StartSessionRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SessionResponse:
    """Start or restart a learner session for a published lesson."""

    user = await _get_user(session, payload.user_id)
    lesson = await _get_published_lesson(session, payload.lesson_id)
    total_exercises = await _exercise_count(session, lesson.id)
    if total_exercises == 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Lesson has no exercises.",
        )

    progress = await _scalar_or_none(
        session,
        select(Progress).where(
            Progress.user_id == user.id,
            Progress.lesson_id == lesson.id,
        ),
    )
    if progress is None:
        progress = Progress(
            user_id=user.id,
            lesson_id=lesson.id,
            total_exercises=total_exercises,
        )
        session.add(progress)

    learning_session = await _scalar_or_none(
        session,
        select(LearningSession)
        .where(
            LearningSession.user_id == user.id,
            LearningSession.lesson_id == lesson.id,
            LearningSession.language_pack_id == lesson.pack_id,
            LearningSession.language_pack_version == lesson.pack_version,
            LearningSession.status == "in_progress",
        )
        .order_by(
            LearningSession.last_seen_at.desc(), LearningSession.created_at.desc()
        )
        .limit(1),
    )
    if learning_session is None:
        learning_session = LearningSession(
            user_id=user.id,
            lesson_id=lesson.id,
            language_pack_id=lesson.pack_id,
            language_pack_version=lesson.pack_version,
        )
        session.add(learning_session)

    now = datetime.now(UTC)
    learning_session.last_seen_at = now
    progress.status = "in_progress"
    progress.total_exercises = total_exercises
    progress.completed_at = None

    await session.commit()
    await session.refresh(learning_session)
    return _session_response(learning_session, total_exercises=total_exercises)


@router.get(
    "/sessions/{session_id}/exercise",
    response_model=CurrentExerciseResponse,
)
async def get_current_exercise(
    session_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CurrentExerciseResponse:
    """Return the current exercise for a session."""

    learning_session = await _get_learning_session(session, session_id)
    exercise = await _current_exercise(session, learning_session)
    return CurrentExerciseResponse(
        session_id=learning_session.id,
        status=learning_session.status,
        exercise=_exercise_response(exercise) if exercise is not None else None,
    )


@router.post(
    "/sessions/{session_id}/answers",
    response_model=SubmitAnswerResponse,
)
async def submit_answer(
    session_id: UUID,
    payload: SubmitAnswerRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SubmitAnswerResponse:
    """Submit an answer for the current exercise and advance progress."""

    learning_session = await _get_learning_session(session, session_id)
    if learning_session.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Session is already completed.",
        )

    total_exercises = await _exercise_count(session, learning_session.lesson_id)
    exercise = await _current_exercise(session, learning_session)
    if exercise is None:
        now = datetime.now(UTC)
        learning_session.status = "completed"
        learning_session.completed_at = now
        progress = await _get_or_create_progress(
            session,
            learning_session=learning_session,
            total_exercises=total_exercises,
        )
        progress.status = "completed"
        progress.completed_at = now
        await session.commit()
        await session.refresh(learning_session)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Session has no remaining exercises.",
        )

    is_correct = _score_answer(payload.answer, exercise.answer)
    attempt = Attempt(
        user_id=learning_session.user_id,
        exercise_id=exercise.id,
        learning_session_id=learning_session.id,
        language_pack_id=learning_session.language_pack_id,
        language_pack_version=learning_session.language_pack_version,
        answer={"answer": payload.answer},
        is_correct=is_correct,
        score=_score_value(is_correct),
    )
    session.add(attempt)
    await session.flush()

    now = datetime.now(UTC)
    learning_session.current_exercise_index += 1
    learning_session.last_seen_at = now
    progress = await _get_or_create_progress(
        session,
        learning_session=learning_session,
        total_exercises=total_exercises,
    )
    progress.completed_exercises = max(
        progress.completed_exercises,
        learning_session.current_exercise_index,
    )
    progress.last_attempt_at = now
    if learning_session.current_exercise_index >= total_exercises:
        learning_session.status = "completed"
        learning_session.completed_at = now
        progress.status = "completed"
        progress.completed_at = now
    else:
        progress.status = "in_progress"

    await _update_review_state(
        session,
        learning_session=learning_session,
        exercise=exercise,
        attempt=attempt,
        is_correct=is_correct,
        now=now,
    )

    await session.commit()
    await session.refresh(attempt)
    await session.refresh(learning_session)
    return SubmitAnswerResponse(
        attempt_id=attempt.id,
        exercise_id=exercise.id,
        is_correct=is_correct,
        session_completed=learning_session.status == "completed",
        progress=_session_response(
            learning_session,
            total_exercises=total_exercises,
        ),
    )


@router.get("/users/{user_id}/progress", response_model=list[ProgressResponse])
async def get_progress(
    user_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[ProgressResponse]:
    """Return all known lesson progress for a learner."""

    await _get_user(session, user_id)
    statement = (
        select(Progress, Lesson.title)
        .join(Lesson, Lesson.id == Progress.lesson_id)
        .where(Progress.user_id == user_id)
        .order_by(Lesson.language_code, Lesson.position, Lesson.title)
    )
    rows = (await session.execute(statement)).all()
    return [
        ProgressResponse(
            id=progress.id,
            user_id=progress.user_id,
            lesson_id=progress.lesson_id,
            lesson_title=lesson_title,
            status=progress.status,
            completed_exercises=progress.completed_exercises,
            total_exercises=progress.total_exercises,
            last_attempt_at=progress.last_attempt_at,
            completed_at=progress.completed_at,
        )
        for progress, lesson_title in rows
    ]


@router.get(
    "/users/{user_id}/progress/stats",
    response_model=ProgressStatsResponse,
)
async def get_progress_stats(
    user_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ProgressStatsResponse:
    """Return aggregate learner progress statistics."""

    await _get_user(session, user_id)

    answer_count, correct_answers = (
        await session.execute(
            select(
                func.count(Attempt.id),
                func.count(Attempt.id).filter(Attempt.is_correct.is_(True)),
            ).where(
                Attempt.user_id == user_id,
                Attempt.is_correct.is_not(None),
            )
        )
    ).one()
    last_attempt_at = await session.scalar(
        select(func.max(Attempt.attempted_at)).where(Attempt.user_id == user_id)
    )
    completed_lessons = await session.scalar(
        select(func.count(Progress.id)).where(
            Progress.user_id == user_id,
            Progress.status == "completed",
        )
    )
    active_repetitions = await session.scalar(
        select(func.count(ReviewState.id)).where(
            ReviewState.user_id == user_id,
            ReviewState.status == "active",
        )
    )
    last_session_at = await session.scalar(
        select(func.max(LearningSession.last_seen_at)).where(
            LearningSession.user_id == user_id
        )
    )
    last_progress_at = await session.scalar(
        select(func.max(Progress.last_attempt_at)).where(Progress.user_id == user_id)
    )

    accuracy = _accuracy(correct_answers or 0, answer_count or 0)
    return ProgressStatsResponse(
        user_id=user_id,
        answer_count=answer_count or 0,
        accuracy=accuracy,
        accuracy_percent=accuracy * 100,
        completed_lessons=completed_lessons or 0,
        active_repetitions=active_repetitions or 0,
        last_activity_at=_latest_datetime(
            last_attempt_at,
            last_progress_at,
            last_session_at,
        ),
    )


@router.get("/users/{user_id}/sessions/active", response_model=list[SessionResponse])
async def get_active_sessions(
    user_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[SessionResponse]:
    """Return active durable sessions for a learner."""

    await _get_user(session, user_id)
    totals = (
        select(func.count(Exercise.id))
        .where(Exercise.lesson_id == LearningSession.lesson_id)
        .correlate(LearningSession)
        .scalar_subquery()
    )
    rows = (
        await session.execute(
            select(LearningSession, totals.label("total_exercises"))
            .where(
                LearningSession.user_id == user_id,
                LearningSession.status == "in_progress",
            )
            .order_by(
                LearningSession.last_seen_at.desc(), LearningSession.created_at.desc()
            )
        )
    ).all()
    return [
        _session_response(learning_session, total_exercises=total_exercises)
        for learning_session, total_exercises in rows
    ]


@router.get("/users/{user_id}/review", response_model=ReviewQueueResponse)
async def get_review_queue(
    user_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: Annotated[int, Query(ge=1, le=50)] = 5,
) -> ReviewQueueResponse:
    """Return active missed exercises for mistake review."""

    await _get_user(session, user_id)

    statement = (
        select(ReviewState, Exercise)
        .join(Exercise, Exercise.id == ReviewState.exercise_id)
        .where(
            ReviewState.user_id == user_id,
            ReviewState.status == "active",
        )
        .order_by(ReviewState.due_at, ReviewState.updated_at, ReviewState.id)
        .limit(limit)
    )
    rows = (await session.execute(statement)).all()
    return ReviewQueueResponse(
        user_id=user_id,
        cards=[
            ReviewCardResponse(
                exercise_id=exercise.id,
                prompt=exercise.prompt,
                expected_answer=_expected_answer_text(exercise.answer),
                incorrect_attempts=review_state.incorrect_count,
                last_attempted_at=review_state.updated_at,
            )
            for review_state, exercise in rows
        ],
    )


async def _scalar_or_none(
    session: AsyncSession,
    statement: Select[tuple[ModelT]],
) -> ModelT | None:
    return (await session.execute(statement)).scalar_one_or_none()


async def _get_user(session: AsyncSession, user_id: UUID) -> User:
    user = await _scalar_or_none(session, select(User).where(User.id == user_id))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )
    return user


async def _get_published_lesson(session: AsyncSession, lesson_id: UUID) -> Lesson:
    lesson = await _scalar_or_none(
        session,
        select(Lesson).where(Lesson.id == lesson_id, Lesson.is_published.is_(True)),
    )
    if lesson is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Published lesson not found.",
        )
    return lesson


async def _get_learning_session(
    session: AsyncSession,
    learning_session_id: UUID,
) -> LearningSession:
    learning_session = await _scalar_or_none(
        session,
        select(LearningSession).where(LearningSession.id == learning_session_id),
    )
    if learning_session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found.",
        )
    return learning_session


async def _exercise_count(session: AsyncSession, lesson_id: UUID) -> int:
    count = await session.scalar(
        select(func.count(Exercise.id)).where(Exercise.lesson_id == lesson_id)
    )
    return count or 0


async def _current_exercise(
    session: AsyncSession,
    learning_session: LearningSession,
) -> Exercise | None:
    if learning_session.status == "completed":
        return None
    statement = (
        select(Exercise)
        .where(Exercise.lesson_id == learning_session.lesson_id)
        .order_by(Exercise.position, Exercise.slug)
        .offset(learning_session.current_exercise_index)
        .limit(1)
    )
    return await _scalar_or_none(session, statement)


async def _get_or_create_progress(
    session: AsyncSession,
    *,
    learning_session: LearningSession,
    total_exercises: int,
) -> Progress:
    progress = await _scalar_or_none(
        session,
        select(Progress).where(
            Progress.user_id == learning_session.user_id,
            Progress.lesson_id == learning_session.lesson_id,
        ),
    )
    if progress is None:
        progress = Progress(
            user_id=learning_session.user_id,
            lesson_id=learning_session.lesson_id,
            total_exercises=total_exercises,
        )
        session.add(progress)
        await session.flush()
    progress.total_exercises = total_exercises
    return progress


async def _update_review_state(
    session: AsyncSession,
    *,
    learning_session: LearningSession,
    exercise: Exercise,
    attempt: Attempt,
    is_correct: bool | None,
    now: datetime,
) -> None:
    if is_correct is None:
        return

    review_state = await _scalar_or_none(
        session,
        select(ReviewState).where(
            ReviewState.user_id == learning_session.user_id,
            ReviewState.exercise_id == exercise.id,
            ReviewState.language_pack_id == learning_session.language_pack_id,
            ReviewState.language_pack_version == learning_session.language_pack_version,
        ),
    )

    if is_correct:
        if review_state is not None:
            review_state.status = "mastered"
            review_state.last_attempt_id = attempt.id
            review_state.learning_session_id = learning_session.id
        return

    if review_state is None:
        review_state = ReviewState(
            user_id=learning_session.user_id,
            lesson_id=learning_session.lesson_id,
            exercise_id=exercise.id,
            learning_session_id=learning_session.id,
            language_pack_id=learning_session.language_pack_id,
            language_pack_version=learning_session.language_pack_version,
            due_at=_review_due_at(now, incorrect_count=1),
            last_attempt_id=attempt.id,
        )
        session.add(review_state)
        return

    review_state.status = "active"
    review_state.incorrect_count += 1
    review_state.due_at = _review_due_at(
        now,
        incorrect_count=review_state.incorrect_count,
    )
    review_state.last_attempt_id = attempt.id
    review_state.learning_session_id = learning_session.id


def _review_due_at(now: datetime, *, incorrect_count: int) -> datetime:
    interval_index = min(incorrect_count, len(REVIEW_INTERVAL_DAYS)) - 1
    return now + timedelta(days=REVIEW_INTERVAL_DAYS[interval_index])


def _session_response(
    learning_session: LearningSession,
    *,
    total_exercises: int,
) -> SessionResponse:
    return SessionResponse(
        session_id=learning_session.id,
        user_id=learning_session.user_id,
        lesson_id=learning_session.lesson_id,
        status=learning_session.status,
        completed_exercises=learning_session.current_exercise_index,
        total_exercises=total_exercises,
        language_pack_id=learning_session.language_pack_id,
        language_pack_version=learning_session.language_pack_version,
    )


def _exercise_response(exercise: Exercise) -> ExerciseResponse:
    return ExerciseResponse(
        id=exercise.id,
        slug=exercise.slug,
        kind=exercise.kind,
        prompt=exercise.prompt,
        payload=exercise.payload,
        position=exercise.position,
    )


def _score_value(is_correct: bool | None) -> Decimal | None:
    if is_correct is None:
        return None
    return Decimal("1.00") if is_correct else Decimal("0.00")


def _score_answer(
    submitted_answer: str,
    expected_answer: dict[str, object] | None,
) -> bool | None:
    accepted_answers = _accepted_answers(expected_answer)
    if not accepted_answers:
        return None

    normalized_submission = _normalize_answer(submitted_answer)
    return normalized_submission in {
        _normalize_answer(str(accepted_answer)) for accepted_answer in accepted_answers
    }


def _accepted_answers(expected_answer: dict[str, object] | None) -> list[object]:
    if expected_answer is None:
        return []

    for key in ("accepted_answers", "correct_answers", "answers"):
        value = expected_answer.get(key)
        if isinstance(value, list):
            return value

    for key in ("answer", "text", "value"):
        value = expected_answer.get(key)
        if value is not None:
            return [value]

    return []


def _expected_answer_text(expected_answer: dict[str, object] | None) -> str:
    accepted_answers = _accepted_answers(expected_answer)
    if not accepted_answers:
        return ""
    return ", ".join(str(answer) for answer in accepted_answers)


def _normalize_answer(answer: str) -> str:
    return " ".join(answer.casefold().strip().split())


def _accuracy(correct_answers: int, answer_count: int) -> float:
    if answer_count == 0:
        return 0.0
    return correct_answers / answer_count


def _latest_datetime(*values: datetime | None) -> datetime | None:
    return max((value for value in values if value is not None), default=None)
