from datetime import datetime, timedelta, timezone

import pytest

from linguafoundry_core.answers import (
    check_answer,
    expected_answer_text,
    extract_accepted_answers,
    normalize_answer,
)
from linguafoundry_core.review_schedule import calculate_review_due_at


def test_answer_helpers_accept_api_payload_shapes_without_legacy_sessions() -> None:
    assert extract_accepted_answers({"accepted_answers": ["hola", "buenas"]}) == (
        "hola",
        "buenas",
    )
    assert extract_accepted_answers({"correct_answers": ("ciao", "salve")}) == (
        "ciao",
        "salve",
    )
    assert extract_accepted_answers({"answer": "bonjour"}) == ("bonjour",)
    assert expected_answer_text({"answers": ["si", "claro"]}) == "si, claro"


def test_check_answer_normalizes_submissions_and_reports_unscorable_payloads() -> None:
    assert normalize_answer("  BUENOS    Dias ") == "buenos dias"
    assert check_answer(" buenos dias ", {"accepted_answers": ["Buenos Dias"]}) is True
    assert check_answer("buenas noches", {"accepted_answers": ["Buenos Dias"]}) is False
    assert check_answer("anything", {"metadata": "no answers"}) is None


def test_review_schedule_uses_bounded_srs_intervals() -> None:
    reviewed_at = datetime(2026, 6, 19, 12, 0, tzinfo=timezone.utc)

    assert calculate_review_due_at(reviewed_at, incorrect_count=1) == (
        reviewed_at + timedelta(days=1)
    )
    assert calculate_review_due_at(reviewed_at, incorrect_count=2) == (
        reviewed_at + timedelta(days=3)
    )
    assert calculate_review_due_at(reviewed_at, incorrect_count=3) == (
        reviewed_at + timedelta(days=7)
    )
    assert calculate_review_due_at(reviewed_at, incorrect_count=4) == (
        reviewed_at + timedelta(days=14)
    )
    assert calculate_review_due_at(reviewed_at, incorrect_count=99) == (
        reviewed_at + timedelta(days=14)
    )


def test_review_schedule_rejects_non_durable_timestamps_and_counts() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        calculate_review_due_at(datetime(2026, 6, 19, 12, 0))

    with pytest.raises(ValueError, match="positive"):
        calculate_review_due_at(
            datetime(2026, 6, 19, 12, 0, tzinfo=timezone.utc),
            incorrect_count=0,
        )
