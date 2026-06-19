from services.api.app.config import Settings
from services.api.app.main import create_app
from services.api.app.routers.learning import _score_answer, _score_value


def test_openapi_schema_includes_learning_endpoints() -> None:
    app = create_app(Settings(app_env="test"))

    schema = app.openapi()

    assert "/learning/users" in schema["paths"]
    assert "/learning/lessons" in schema["paths"]
    assert "/learning/sessions" in schema["paths"]
    assert "/learning/sessions/{session_id}/exercise" in schema["paths"]
    assert "/learning/sessions/{session_id}/answers" in schema["paths"]
    assert "/learning/users/{user_id}/progress" in schema["paths"]


def test_score_answer_accepts_normalized_answer_variants() -> None:
    expected_answer = {"accepted_answers": ["Buenos dias", "Buen dia"]}

    assert _score_answer("  buenos   DIAS ", expected_answer) is True
    assert _score_answer("hola", expected_answer) is False


def test_score_answer_returns_none_without_answer_key() -> None:
    assert _score_answer("hola", None) is None
    assert _score_value(None) is None
