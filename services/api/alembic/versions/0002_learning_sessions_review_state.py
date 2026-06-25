"""Add durable learning session and review state.

Revision ID: 0002_learning_sessions_review_state
Revises: 0001_initial_schema
Create Date: 2026-06-25
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0002_learning_sessions_review_state"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "alembic_version",
        "version_num",
        existing_type=sa.String(length=32),
        type_=sa.String(length=128),
        existing_nullable=False,
    )

    op.add_column(
        "lessons",
        sa.Column(
            "pack_id",
            sa.String(length=128),
            server_default=sa.text("'legacy'"),
            nullable=False,
        ),
    )
    op.add_column(
        "lessons",
        sa.Column(
            "pack_version",
            sa.String(length=32),
            server_default=sa.text("'1.0'"),
            nullable=False,
        ),
    )
    op.drop_constraint("uq_lessons_language_slug", "lessons", type_="unique")
    op.create_unique_constraint(
        "uq_lessons_pack_version_slug",
        "lessons",
        ["pack_id", "pack_version", "slug"],
    )

    op.create_table(
        "learning_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lesson_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("language_pack_id", sa.String(length=128), nullable=False),
        sa.Column("language_pack_version", sa.String(length=32), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default=sa.text("'in_progress'"),
            nullable=False,
        ),
        sa.Column(
            "current_exercise_index",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["lesson_id"], ["lessons.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_learning_sessions_lesson_id"),
        "learning_sessions",
        ["lesson_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_learning_sessions_user_id"),
        "learning_sessions",
        ["user_id"],
        unique=False,
    )

    op.add_column(
        "attempts",
        sa.Column(
            "learning_session_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.add_column(
        "attempts",
        sa.Column(
            "language_pack_id",
            sa.String(length=128),
            server_default=sa.text("'legacy'"),
            nullable=False,
        ),
    )
    op.add_column(
        "attempts",
        sa.Column(
            "language_pack_version",
            sa.String(length=32),
            server_default=sa.text("'1.0'"),
            nullable=False,
        ),
    )
    op.create_foreign_key(
        "fk_attempts_learning_session_id_learning_sessions",
        "attempts",
        "learning_sessions",
        ["learning_session_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_attempts_learning_session_id"),
        "attempts",
        ["learning_session_id"],
        unique=False,
    )

    op.create_table(
        "review_states",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lesson_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("exercise_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "learning_session_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("language_pack_id", sa.String(length=128), nullable=False),
        sa.Column("language_pack_version", sa.String(length=32), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default=sa.text("'active'"),
            nullable=False,
        ),
        sa.Column(
            "incorrect_count",
            sa.Integer(),
            server_default=sa.text("1"),
            nullable=False,
        ),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_attempt_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["exercise_id"], ["exercises.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["last_attempt_id"], ["attempts.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["lesson_id"], ["lessons.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["learning_session_id"],
            ["learning_sessions.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "exercise_id",
            "language_pack_id",
            "language_pack_version",
            name="uq_review_states_user_exercise_pack_version",
        ),
    )
    op.create_index(
        op.f("ix_review_states_exercise_id"),
        "review_states",
        ["exercise_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_review_states_learning_session_id"),
        "review_states",
        ["learning_session_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_review_states_lesson_id"),
        "review_states",
        ["lesson_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_review_states_user_id"),
        "review_states",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_review_states_user_id"), table_name="review_states")
    op.drop_index(op.f("ix_review_states_lesson_id"), table_name="review_states")
    op.drop_index(
        op.f("ix_review_states_learning_session_id"),
        table_name="review_states",
    )
    op.drop_index(op.f("ix_review_states_exercise_id"), table_name="review_states")
    op.drop_table("review_states")

    op.drop_index(op.f("ix_attempts_learning_session_id"), table_name="attempts")
    op.drop_constraint(
        "fk_attempts_learning_session_id_learning_sessions",
        "attempts",
        type_="foreignkey",
    )
    op.drop_column("attempts", "language_pack_version")
    op.drop_column("attempts", "language_pack_id")
    op.drop_column("attempts", "learning_session_id")

    op.drop_index(op.f("ix_learning_sessions_user_id"), table_name="learning_sessions")
    op.drop_index(
        op.f("ix_learning_sessions_lesson_id"), table_name="learning_sessions"
    )
    op.drop_table("learning_sessions")

    op.drop_constraint("uq_lessons_pack_version_slug", "lessons", type_="unique")
    op.create_unique_constraint(
        "uq_lessons_language_slug",
        "lessons",
        ["language_code", "slug"],
    )
    op.drop_column("lessons", "pack_version")
    op.drop_column("lessons", "pack_id")
