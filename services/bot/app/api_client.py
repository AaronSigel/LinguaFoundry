"""Minimal API client used by the Telegram bot adapter."""

from __future__ import annotations

import json
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen


class ApiClientError(RuntimeError):
    """Raised when the bot cannot reach the backend API."""


class ApiClient:
    """Small HTTP client for backend API calls needed by bot handlers."""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def get_json(self, path: str) -> dict[str, Any]:
        """Return a JSON object from an API path."""

        request = Request(
            f"{self.base_url}/{path.lstrip('/')}",
            headers={"Accept": "application/json"},
            method="GET",
        )
        try:
            with urlopen(request, timeout=10) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (OSError, URLError, json.JSONDecodeError) as exc:
            raise ApiClientError(str(exc)) from exc

        if not isinstance(payload, dict):
            raise ApiClientError("API response was not a JSON object")
        return payload

    def health(self) -> dict[str, Any]:
        """Return backend API health metadata."""

        return self.get_json("/health")
