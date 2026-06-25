from datetime import datetime, timezone

from services.api.app.config import Settings
from services.api.app.main import create_app
from services.api.app.routers.learning import (
    _accuracy,
    _expected_answer_text,
    _latest_datetime,
    _score_answer,
    _score_value,
)


def test_openapi_schema_includes_learning_endpoints() -> None:
    app = create_app(Settings(app_env="test"))

    schema = app.openapi()

    assert "/learning/users" in schema["paths"]
    assert "/learning/lessons" in schema["paths"]
    assert "/learning/sessions" in schema["paths"]
    assert "/learning/sessions/{session_id}/exercise" in schema["paths"]
    assert "/learning/sessions/{session_id}/answers" in schema["paths"]
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
