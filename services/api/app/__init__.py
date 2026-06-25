"""Application package for the LinguaFoundry API service."""

from typing import Any

__all__ = ["create_app"]


def __getattr__(name: str) -> Any:
    """Lazily expose the FastAPI app factory without eager router imports."""

    if name == "create_app":
        from services.api.app.main import create_app

        return create_app
    raise AttributeError(name)
