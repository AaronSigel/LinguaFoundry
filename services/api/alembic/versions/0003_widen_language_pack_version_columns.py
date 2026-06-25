"""Widen persisted language pack version columns.

Revision ID: 0003_widen_language_pack_version_columns
Revises: 0002_learning_sessions_review_state
Create Date: 2026-06-25
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0003_widen_language_pack_version_columns"
down_revision: str | None = "0002_learning_sessions_review_state"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


PACK_VERSION_COLUMNS: tuple[tuple[str, str], ...] = (
    ("lessons", "pack_version"),
    ("learning_sessions", "language_pack_version"),
    ("attempts", "language_pack_version"),
    ("review_states", "language_pack_version"),
)


def upgrade() -> None:
    for table_name, column_name in PACK_VERSION_COLUMNS:
        op.alter_column(
            table_name,
            column_name,
            existing_type=sa.String(length=32),
            type_=sa.String(length=128),
            existing_nullable=False,
        )


def downgrade() -> None:
    # 0002 now defines these columns at 128 characters. Keep downgrade non-lossy.
    pass
