import asyncio

import httpx

from services.api.app.config import Settings
from services.api.app.dependencies import get_domain_context
from services.api.app.main import create_app


def test_health_endpoint_returns_environment_metadata() -> None:
    app = create_app(
        Settings(
            app_env="test",
            log_level="DEBUG",
            service_name="test-api",
        )
    )

    async def domain_context() -> dict[str, str]:
        return {"status": "ready"}

    app.dependency_overrides[get_domain_context] = domain_context

    async def request_health() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.get("/health")

    response = asyncio.run(request_health())

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "test-api",
        "environment": "test",
        "domain": "ready",
    }


def test_openapi_schema_includes_health_endpoint() -> None:
    app = create_app(Settings(app_env="test"))

    schema = app.openapi()

    assert "/health" in schema["paths"]
