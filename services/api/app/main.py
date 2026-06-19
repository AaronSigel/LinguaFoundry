"""FastAPI application factory for the API service."""

from fastapi import FastAPI

from services.api.app.config import Settings, get_settings
from services.api.app.routers.health import router as health_router
from services.api.app.routers.learning import router as learning_router


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""

    resolved_settings = settings or get_settings()
    app = FastAPI(
        title="LinguaFoundry API",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    app.state.settings = resolved_settings
    app.include_router(health_router)
    app.include_router(learning_router)
    return app


app = create_app()
