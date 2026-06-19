import asyncio
from types import SimpleNamespace

from services.api.app.config import Settings
from services.api.app.main import create_app
from services.api.app.routers.health import health_check


def test_health_endpoint_returns_environment_metadata() -> None:
    settings = Settings(
        app_env="test",
        log_level="DEBUG",
        service_name="test-api",
    )
    request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(settings=settings))
    )

    response = asyncio.run(health_check(request, {"status": "not_configured"}))

    assert response.model_dump() == {
        "status": "ok",
        "service": "test-api",
        "environment": "test",
        "domain": "not_configured",
    }


def test_openapi_schema_includes_health_endpoint() -> None:
    app = create_app(Settings(app_env="test"))

    schema = app.openapi()

    assert "/health" in schema["paths"]
