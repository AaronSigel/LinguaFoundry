from services.api.app.config import Settings
from services.api.app.main import create_app


def test_openapi_schema_supports_mvp_smoke_scenario() -> None:
    app = create_app(Settings(app_env="test"))

    schema = app.openapi()
    paths = schema["paths"]

    expected_route_sequence = [
        ("get", "/health"),
        ("post", "/learning/users"),
        ("get", "/learning/lessons"),
        ("post", "/learning/sessions"),
        ("get", "/learning/sessions/{session_id}/exercise"),
        ("post", "/learning/sessions/{session_id}/answers"),
        ("get", "/learning/users/{user_id}/progress"),
        ("get", "/learning/users/{user_id}/progress/stats"),
        ("get", "/learning/users/{user_id}/review"),
    ]

    for method, path in expected_route_sequence:
        assert method in paths[path]


def test_openapi_schema_exposes_smoke_progress_fields() -> None:
    app = create_app(Settings(app_env="test"))

    schemas = app.openapi()["components"]["schemas"]

    assert {
        "session_completed",
        "is_correct",
        "progress",
    }.issubset(schemas["SubmitAnswerResponse"]["properties"])
    assert {
        "answer_count",
        "accuracy",
        "accuracy_percent",
        "completed_lessons",
        "active_repetitions",
        "last_activity_at",
    }.issubset(schemas["ProgressStatsResponse"]["properties"])
    assert {"user_id", "cards"}.issubset(schemas["ReviewQueueResponse"]["properties"])
