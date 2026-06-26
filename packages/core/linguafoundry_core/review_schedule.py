"""Shared lightweight review scheduling helpers."""

from __future__ import annotations

from datetime import datetime, timedelta


REVIEW_INTERVAL_DAYS = (1, 3, 7, 14)


def calculate_review_due_at(
    reviewed_at: datetime, incorrect_count: int = 1
) -> datetime:
    """Calculate the next lightweight SRS review timestamp."""

    if reviewed_at.tzinfo is None:
        raise ValueError("reviewed_at must be timezone-aware.")
    if incorrect_count < 1:
        raise ValueError("incorrect_count must be positive.")

    interval_index = min(incorrect_count - 1, len(REVIEW_INTERVAL_DAYS) - 1)
    return reviewed_at + timedelta(days=REVIEW_INTERVAL_DAYS[interval_index])
