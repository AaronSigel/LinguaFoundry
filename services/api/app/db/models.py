"""Minimal database schema for language learning workflows."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from services.api.app.db.base import Base


class User(Base):
    """Learner identity known to the API."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    telegram_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64))
    first_name: Mapped[str | None] = mapped_column(String(128))
    last_name: Mapped[str | None] = mapped_column(String(128))
    interface_language: Mapped[str | None] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    attempts: Mapped[list["Attempt"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    learning_sessions: Mapped[list["LearningSession"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    progress_entries: Mapped[list["Progress"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    review_states: Mapped[list["ReviewState"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


class Lesson(Base):
    """A lesson from a language content pack."""

    __tablename__ = "lessons"
    __table_args__ = (
        UniqueConstraint(
            "pack_id",
            "pack_version",
            "slug",
            name="uq_lessons_pack_version_slug",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    language_code: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    pack_id: Mapped[str] = mapped_column(String(128), nullable=False)
    pack_version: Mapped[str] = mapped_column(String(128), nullable=False)
    slug: Mapped[str] = mapped_column(String(128), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    level: Mapped[str | None] = mapped_column(String(32))
    position: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    is_published: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    exercises: Mapped[list["Exercise"]] = relationship(
        back_populates="lesson",
        cascade="all, delete-orphan",
    )
    learning_sessions: Mapped[list["LearningSession"]] = relationship(
        back_populates="lesson",
        cascade="all, delete-orphan",
    )
    progress_entries: Mapped[list["Progress"]] = relationship(
        back_populates="lesson",
        cascade="all, delete-orphan",
    )
    review_states: Mapped[list["ReviewState"]] = relationship(
        back_populates="lesson",
        cascade="all, delete-orphan",
    )

    @property
    def content_version(self) -> str:
        """Content version persisted in the legacy pack_version column."""

        return self.pack_version

    @content_version.setter
    def content_version(self, value: str) -> None:
        self.pack_version = value


class Exercise(Base):
    """An individual practice item in a lesson."""

    __tablename__ = "exercises"
    __table_args__ = (
        UniqueConstraint("lesson_id", "slug", name="uq_exercises_lesson_slug"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    lesson_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("lessons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    slug: Mapped[str] = mapped_column(String(128), nullable=False)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    answer: Mapped[dict[str, object] | None] = mapped_column(JSONB)
    position: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    lesson: Mapped[Lesson] = relationship(back_populates="exercises")
    attempts: Mapped[list["Attempt"]] = relationship(
        back_populates="exercise",
        cascade="all, delete-orphan",
    )
    review_states: Mapped[list["ReviewState"]] = relationship(
        back_populates="exercise",
        cascade="all, delete-orphan",
    )


class LearningSession(Base):
    """Durable active lesson session state for a learner."""

    __tablename__ = "learning_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    lesson_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("lessons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    language_pack_id: Mapped[str] = mapped_column(String(128), nullable=False)
    language_pack_version: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="in_progress",
        server_default=text("'in_progress'"),
    )
    current_exercise_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user: Mapped[User] = relationship(back_populates="learning_sessions")
    lesson: Mapped[Lesson] = relationship(back_populates="learning_sessions")
    attempts: Mapped[list["Attempt"]] = relationship(back_populates="learning_session")
    review_states: Mapped[list["ReviewState"]] = relationship(
        back_populates="learning_session"
    )


class Attempt(Base):
    """A learner answer submission for an exercise."""

    __tablename__ = "attempts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    exercise_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("exercises.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    learning_session_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("learning_sessions.id", ondelete="SET NULL"),
        index=True,
    )
    language_pack_id: Mapped[str] = mapped_column(String(128), nullable=False)
    language_pack_version: Mapped[str] = mapped_column(String(128), nullable=False)
    answer: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    is_correct: Mapped[bool | None] = mapped_column(Boolean)
    score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    attempted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    user: Mapped[User] = relationship(back_populates="attempts")
    exercise: Mapped[Exercise] = relationship(back_populates="attempts")
    learning_session: Mapped[LearningSession | None] = relationship(
        back_populates="attempts"
    )


class Progress(Base):
    """Per-user lesson progress."""

    __tablename__ = "progress"
    __table_args__ = (
        UniqueConstraint("user_id", "lesson_id", name="uq_progress_user_lesson"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    lesson_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("lessons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="not_started",
    )
    completed_exercises: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    total_exercises: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user: Mapped[User] = relationship(back_populates="progress_entries")
    lesson: Mapped[Lesson] = relationship(back_populates="progress_entries")


class ReviewState(Base):
    """Durable spaced-review state for a learner and exercise."""

    __tablename__ = "review_states"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "exercise_id",
            "language_pack_id",
            "language_pack_version",
            name="uq_review_states_user_exercise_pack_version",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    lesson_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("lessons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    exercise_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("exercises.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    learning_session_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("learning_sessions.id", ondelete="SET NULL"),
        index=True,
    )
    language_pack_id: Mapped[str] = mapped_column(String(128), nullable=False)
    language_pack_version: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="active",
        server_default=text("'active'"),
    )
    incorrect_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default=text("1"),
    )
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_attempt_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("attempts.id", ondelete="SET NULL"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user: Mapped[User] = relationship(back_populates="review_states")
    lesson: Mapped[Lesson] = relationship(back_populates="review_states")
    exercise: Mapped[Exercise] = relationship(back_populates="review_states")
    learning_session: Mapped[LearningSession | None] = relationship(
        back_populates="review_states"
    )
    last_attempt: Mapped[Attempt | None] = relationship(foreign_keys=[last_attempt_id])
