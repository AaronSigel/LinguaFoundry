"""Minimal API client used by the Telegram bot adapter."""

from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class ApiClientError(RuntimeError):
    """Raised when the bot cannot reach the backend API."""


class ApiClient:
    """Small HTTP client for backend API calls needed by bot handlers."""

    def __init__(self, base_url: str, api_key: str = "") -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def _headers(self, content_type: str | None = None) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if content_type is not None:
            headers["Content-Type"] = content_type
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    def get_json(self, path: str) -> dict[str, Any]:
        """Return a JSON object from an API path."""

        request = Request(
            f"{self.base_url}/{path.lstrip('/')}",
            headers=self._headers(),
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

    def post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Post a JSON object to an API path and return a JSON object."""

        data = json.dumps(payload).encode("utf-8")
        request = Request(
            f"{self.base_url}/{path.lstrip('/')}",
            data=data,
            headers=self._headers("application/json"),
            method="POST",
        )
        try:
            with urlopen(request, timeout=10) as response:
                response_payload = json.loads(response.read().decode("utf-8"))
        except (OSError, HTTPError, URLError, json.JSONDecodeError) as exc:
            raise ApiClientError(str(exc)) from exc

        if not isinstance(response_payload, dict):
            raise ApiClientError("API response was not a JSON object")
        return response_payload

    def health(self) -> dict[str, Any]:
        """Return backend API health metadata."""

        return self.get_json("/health")

    def register_telegram_user(self, telegram_id: int) -> dict[str, Any]:
        """Register or resolve a learner by Telegram user id."""

        return self.post_json("/learning/users", {"telegram_id": telegram_id})

    def progress_stats(self, user_id: str) -> dict[str, Any]:
        """Return aggregate learner progress statistics."""

        return self.get_json(f"/learning/users/{user_id}/progress/stats")

    def list_lessons(self, language_code: str | None = None) -> list[dict[str, Any]]:
        """Return published lessons available for Telegram learners."""

        path = "/learning/lessons"
        if language_code is not None:
            path = f"{path}?{urlencode({'language_code': language_code})}"
        payload = self.get_json_list(path)
        return payload

    def start_session(self, user_id: str, lesson_id: str) -> dict[str, Any]:
        """Start a learning session for a learner and lesson."""

        return self.post_json(
            "/learning/sessions",
            {"user_id": user_id, "lesson_id": lesson_id},
        )

    def current_exercise(self, session_id: str) -> dict[str, Any]:
        """Return the current exercise for a session."""

        return self.get_json(f"/learning/sessions/{session_id}/exercise")

    def submit_answer(self, session_id: str, answer: str) -> dict[str, Any]:
        """Submit a text answer for the current session exercise."""

        return self.post_json(
            f"/learning/sessions/{session_id}/answers",
            {"answer": answer},
        )

    def review_queue(self, user_id: str) -> dict[str, Any]:
        """Return missed exercises due for learner review."""

        return self.get_json(f"/learning/users/{user_id}/review")

    def get_json_list(self, path: str) -> list[dict[str, Any]]:
        """Return a JSON object list from an API path."""

        request = Request(
            f"{self.base_url}/{path.lstrip('/')}",
            headers=self._headers(),
            method="GET",
        )
        try:
            with urlopen(request, timeout=10) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (OSError, URLError, json.JSONDecodeError) as exc:
            raise ApiClientError(str(exc)) from exc

        if not isinstance(payload, list) or not all(
            isinstance(item, dict) for item in payload
        ):
            raise ApiClientError("API response was not a JSON object list")
        return payload
