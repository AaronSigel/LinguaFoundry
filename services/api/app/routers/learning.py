"""Learning workflow endpoints."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated, TypeVar
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from linguafoundry_core import (
    Attempt as CoreAttempt,
    AttemptResult,
    Exercise as CoreExercise,
    ExerciseType,
    build_mistake_review_queue,
)
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from services.api.app.db.database import get_session
from services.api.app.db.models import Attempt, Exercise, Lesson, Progress, User

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
    """Learning session state backed by a progress row."""

    session_id: UUID
    user_id: UUID
    lesson_id: UUID
    status: str
    completed_exercises: int
    total_exercises: int


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
    """Due mistake review queue for a learner."""

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
        progress = Progress(user_id=user.id, lesson_id=lesson.id)
        session.add(progress)

    progress.status = "in_progress"
    progress.completed_exercises = 0
    progress.total_exercises = total_exercises
    progress.last_attempt_at = None
    progress.completed_at = None

    await session.commit()
    await session.refresh(progress)
    return _session_response(progress)


@router.get(
    "/sessions/{session_id}/exercise",
    response_model=CurrentExerciseResponse,
)
async def get_current_exercise(
    session_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CurrentExerciseResponse:
    """Return the current exercise for a session."""

    progress = await _get_progress(session, session_id)
    exercise = await _current_exercise(session, progress)
    return CurrentExerciseResponse(
        session_id=progress.id,
        status=progress.status,
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

    progress = await _get_progress(session, session_id)
    if progress.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Session is already completed.",
        )

    exercise = await _current_exercise(session, progress)
    if exercise is None:
        progress.status = "completed"
        progress.completed_at = datetime.now(UTC)
        await session.commit()
        await session.refresh(progress)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Session has no remaining exercises.",
        )

    is_correct = _score_answer(payload.answer, exercise.answer)
    attempt = Attempt(
        user_id=progress.user_id,
        exercise_id=exercise.id,
        answer={"answer": payload.answer},
        is_correct=is_correct,
        score=_score_value(is_correct),
    )
    session.add(attempt)

    progress.completed_exercises += 1
    progress.last_attempt_at = datetime.now(UTC)
    if progress.completed_exercises >= progress.total_exercises:
        progress.status = "completed"
        progress.completed_at = progress.last_attempt_at

    await session.commit()
    await session.refresh(attempt)
    await session.refresh(progress)
    return SubmitAnswerResponse(
        attempt_id=attempt.id,
        exercise_id=exercise.id,
        is_correct=is_correct,
        session_completed=progress.status == "completed",
        progress=_session_response(progress),
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
        select(func.count(Progress.id)).where(
            Progress.user_id == user_id,
            Progress.status == "in_progress",
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
        last_activity_at=_latest_datetime(last_attempt_at, last_progress_at),
    )


@router.get("/users/{user_id}/review", response_model=ReviewQueueResponse)
async def get_review_queue(
    user_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: int = 5,
) -> ReviewQueueResponse:
    """Return exercises whose latest non-skipped attempt was incorrect."""

    await _get_user(session, user_id)
    if limit < 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="limit must be positive.",
        )

    statement = (
        select(Attempt, Exercise)
        .join(Exercise, Exercise.id == Attempt.exercise_id)
        .where(Attempt.user_id == user_id, Attempt.is_correct.is_not(None))
        .order_by(Attempt.attempted_at, Attempt.id)
    )
    rows = (await session.execute(statement)).all()
    attempts = [_core_attempt(attempt) for attempt, _exercise in rows]
    exercises = {
        _exercise.id: _core_exercise(_exercise) for _attempt, _exercise in rows
    }
    cards = [
        ReviewCardResponse(
            exercise_id=UUID(card.exercise_id),
            prompt=card.prompt,
            expected_answer=card.expected_answer,
            incorrect_attempts=card.incorrect_attempts,
            last_attempted_at=card.last_attempted_at,
        )
        for card in build_mistake_review_queue(
            attempts=attempts,
            exercises=exercises.values(),
            user_id=str(user_id),
            limit=limit,
        )
    ]
    return ReviewQueueResponse(user_id=user_id, cards=cards)


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


async def _get_progress(session: AsyncSession, progress_id: UUID) -> Progress:
    progress = await _scalar_or_none(
        session,
        select(Progress).where(Progress.id == progress_id),
    )
    if progress is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found.",
        )
    return progress


async def _exercise_count(session: AsyncSession, lesson_id: UUID) -> int:
    count = await session.scalar(
        select(func.count(Exercise.id)).where(Exercise.lesson_id == lesson_id)
    )
    return count or 0


async def _current_exercise(
    session: AsyncSession,
    progress: Progress,
) -> Exercise | None:
    if progress.status == "completed":
        return None
    statement = (
        select(Exercise)
        .where(Exercise.lesson_id == progress.lesson_id)
        .order_by(Exercise.position, Exercise.slug)
        .offset(progress.completed_exercises)
        .limit(1)
    )
    return await _scalar_or_none(session, statement)


def _session_response(progress: Progress) -> SessionResponse:
    return SessionResponse(
        session_id=progress.id,
        user_id=progress.user_id,
        lesson_id=progress.lesson_id,
        status=progress.status,
        completed_exercises=progress.completed_exercises,
        total_exercises=progress.total_exercises,
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


def _core_attempt(attempt: Attempt) -> CoreAttempt:
    submitted_answer = attempt.answer.get("answer")
    return CoreAttempt(
        id=str(attempt.id),
        user_id=str(attempt.user_id),
        exercise_id=str(attempt.exercise_id),
        submitted_answer=str(submitted_answer) if submitted_answer is not None else "",
        result=AttemptResult.CORRECT
        if attempt.is_correct is True
        else AttemptResult.INCORRECT,
        attempted_at=attempt.attempted_at,
    )


def _core_exercise(exercise: Exercise) -> CoreExercise:
    return CoreExercise(
        id=str(exercise.id),
        lesson_id=str(exercise.lesson_id),
        exercise_type=_core_exercise_type(exercise.kind),
        prompt=exercise.prompt,
        expected_answer=_expected_answer_text(exercise.answer) or "Answer unavailable",
        order=exercise.position,
    )


def _core_exercise_type(kind: str) -> ExerciseType:
    try:
        return ExerciseType(kind)
    except ValueError:
        return ExerciseType.TEXT_INPUT


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
