import pytest

from services.bot.app import main
from services.bot.app.api_client import ApiClientError
from services.bot.app.config import Settings


class FlakyHealthClient:
    attempts = 0
    last_api_key = ""

    def __init__(self, base_url: str, api_key: str = "") -> None:
        self.base_url = base_url
        self.api_key = api_key
        type(self).last_api_key = api_key

    def health(self) -> dict[str, str]:
        type(self).attempts += 1
        if type(self).attempts == 1:
            raise ApiClientError("offline")
        return {"status": "ok"}


class OfflineHealthClient:
    attempts = 0

    def __init__(self, base_url: str, api_key: str = "") -> None:
        self.base_url = base_url
        self.api_key = api_key

    def health(self) -> dict[str, str]:
        type(self).attempts += 1
        raise ApiClientError("offline")


def test_wait_for_api_retries_until_health_passes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sleeps: list[float] = []
    header_value = "local-" + "api-key"
    FlakyHealthClient.attempts = 0
    FlakyHealthClient.last_api_key = ""
    monkeypatch.setattr(main, "ApiClient", FlakyHealthClient)
    monkeypatch.setattr(main.time, "monotonic", lambda: 0.0)
    monkeypatch.setattr(main.time, "sleep", sleeps.append)

    main.wait_for_api(
        Settings(
            api_base_url="http://api:8000",
            api_key=header_value,
            api_ready_timeout_seconds=10,
            api_ready_interval_seconds=0.25,
        )
    )

    assert FlakyHealthClient.attempts == 2
    assert FlakyHealthClient.last_api_key == header_value
    assert sleeps == [0.25]


def test_wait_for_api_times_out_after_retry_window(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monotonic_values = iter([0.0, 0.5, 1.0])
    sleeps: list[float] = []
    OfflineHealthClient.attempts = 0
    monkeypatch.setattr(main, "ApiClient", OfflineHealthClient)
    monkeypatch.setattr(main.time, "monotonic", lambda: next(monotonic_values))
    monkeypatch.setattr(main.time, "sleep", sleeps.append)

    with pytest.raises(RuntimeError, match="API readiness check timed out"):
        main.wait_for_api(
            Settings(
                api_base_url="http://api:8000",
                api_ready_timeout_seconds=1,
                api_ready_interval_seconds=0.25,
            )
        )

    assert OfflineHealthClient.attempts == 2
    assert sleeps == [0.25]
