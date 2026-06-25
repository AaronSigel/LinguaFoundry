import asyncio

import httpx
import pytest
from fastapi.routing import APIRoute

from services.api.app.config import Settings
from services.api.app.main import create_app
from services.api.app.routers.health import router as health_router


def test_health_endpoint_returns_environment_metadata() -> None:
    app = create_app(
        Settings(
            app_env="test",
            log_level="DEBUG",
            service_name="test-api",
        )
    )

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


def test_health_endpoint_has_no_dependency_hooks() -> None:
    health_routes = [
        route
        for route in health_router.routes
        if isinstance(route, APIRoute) and route.path == "/health"
    ]

    assert len(health_routes) == 1
    health_route = health_routes[0]

    assert health_route.methods == {"GET"}
    assert health_route.dependant.dependencies == []


def test_production_requires_api_key() -> None:
    with pytest.raises(RuntimeError, match="API_KEY is required"):
        create_app(Settings(app_env="production", api_key=""))


def test_api_key_protects_non_public_routes() -> None:
    header_value = "local-" + "api-key"
    app = create_app(Settings(app_env="test", api_key=header_value))

    async def request_private_path(
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.get("/private-path", headers=headers)

    unauthorized_response = asyncio.run(request_private_path())
    authorized_response = asyncio.run(request_private_path({"X-API-Key": header_value}))

    assert unauthorized_response.status_code == 401
    assert authorized_response.status_code == 404


def test_api_key_allows_public_health_and_schema_routes() -> None:
    app = create_app(Settings(app_env="test", api_key="local-" + "api-key"))

    async def request_public_paths() -> list[httpx.Response]:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return [
                await client.get("/health"),
                await client.get("/openapi.json"),
            ]

    health_response, schema_response = asyncio.run(request_public_paths())

    assert health_response.status_code == 200
    assert schema_response.status_code == 200
