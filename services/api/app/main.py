"""FastAPI application factory for the API service."""

from hmac import compare_digest

from fastapi import FastAPI
from fastapi import Request
from fastapi.responses import JSONResponse

from services.api.app.config import Settings, get_settings
from services.api.app.logging import configure_logging
from services.api.app.routers.health import router as health_router
from services.api.app.routers.learning import router as learning_router

PUBLIC_PATHS = {"/health", "/openapi.json", "/docs", "/redoc"}


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""

    resolved_settings = settings or get_settings()
    configure_logging(resolved_settings.log_level)
    app = FastAPI(
        title="LinguaFoundry API",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    app.state.settings = resolved_settings

    @app.middleware("http")
    async def require_api_key(request: Request, call_next):
        configured_key = resolved_settings.api_key
        if configured_key and request.url.path not in PUBLIC_PATHS:
            supplied_key = request.headers.get("X-API-Key", "")
            if not compare_digest(supplied_key, configured_key):
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Invalid or missing API key"},
                )
        return await call_next(request)

    app.include_router(health_router)
    app.include_router(learning_router)
    return app


app = create_app()
