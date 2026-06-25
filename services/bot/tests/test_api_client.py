import json
from typing import Any
from urllib.request import Request

import pytest

from services.bot.app import api_client
from services.bot.app.api_client import ApiClient, ApiClientError


class FakeResponse:
    def __init__(self, payload: object) -> None:
        self.payload = payload

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


class RecordingUrlopen:
    def __init__(self, responses: list[object]) -> None:
        self.responses = responses
        self.requests: list[Request] = []
        self.timeouts: list[int] = []

    def __call__(self, request: Request, timeout: int) -> FakeResponse:
        self.requests.append(request)
        self.timeouts.append(timeout)
        return FakeResponse(self.responses.pop(0))


def _json_body(request: Request) -> dict[str, Any]:
    data = request.data
    assert data is not None
    body = json.loads(data.decode("utf-8"))
    assert isinstance(body, dict)
    return body


def test_api_client_uses_learning_workflow_endpoints(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorder = RecordingUrlopen(
        [
            {"id": "user-1"},
            [{"id": "lesson-1", "slug": "intro"}],
            {"session_id": "session-1"},
            {"exercise": {"prompt": "Translate: hello"}},
            {"is_correct": True},
            {"answer_count": 1},
            {"cards": []},
        ]
    )
    monkeypatch.setattr(api_client, "urlopen", recorder)
    client = ApiClient("https://api.example.test/")

    assert client.register_telegram_user(123) == {"id": "user-1"}
    assert client.list_lessons(language_code="fr") == [
        {"id": "lesson-1", "slug": "intro"}
    ]
    assert client.start_session("user-1", "lesson-1") == {"session_id": "session-1"}
    assert client.current_exercise("session-1") == {
        "exercise": {"prompt": "Translate: hello"}
    }
    assert client.submit_answer("session-1", "bonjour") == {"is_correct": True}
    assert client.progress_stats("user-1") == {"answer_count": 1}
    assert client.review_queue("user-1") == {"cards": []}

    assert [request.get_method() for request in recorder.requests] == [
        "POST",
        "GET",
        "POST",
        "GET",
        "POST",
        "GET",
        "GET",
    ]
    assert [request.full_url for request in recorder.requests] == [
        "https://api.example.test/learning/users",
        "https://api.example.test/learning/lessons?language_code=fr",
        "https://api.example.test/learning/sessions",
        "https://api.example.test/learning/sessions/session-1/exercise",
        "https://api.example.test/learning/sessions/session-1/answers",
        "https://api.example.test/learning/users/user-1/progress/stats",
        "https://api.example.test/learning/users/user-1/review",
    ]
    assert _json_body(recorder.requests[0]) == {"telegram_id": 123}
    assert _json_body(recorder.requests[2]) == {
        "user_id": "user-1",
        "lesson_id": "lesson-1",
    }
    assert _json_body(recorder.requests[4]) == {"answer": "bonjour"}
    assert recorder.timeouts == [10, 10, 10, 10, 10, 10, 10]


def test_api_client_sends_configured_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorder = RecordingUrlopen([{"status": "ok"}])
    monkeypatch.setattr(api_client, "urlopen", recorder)
    header_value = "local-" + "api-key"
    client = ApiClient("https://api.example.test/", api_key=header_value)

    assert client.health() == {"status": "ok"}

    assert recorder.requests[0].get_header("X-api-key") == header_value


def test_api_client_rejects_non_object_response_for_object_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(api_client, "urlopen", RecordingUrlopen([[]]))
    client = ApiClient("https://api.example.test")

    with pytest.raises(ApiClientError, match="JSON object"):
        client.health()


def test_api_client_rejects_non_list_response_for_lesson_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(api_client, "urlopen", RecordingUrlopen([{"lessons": []}]))
    client = ApiClient("https://api.example.test")

    with pytest.raises(ApiClientError, match="JSON object list"):
        client.list_lessons()
