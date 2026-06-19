"""Telegram Bot API transport and update parsing."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class IncomingMessage:
    """Telegram message fields needed by bot command handlers."""

    chat_id: int
    text: str

    @property
    def command(self) -> str | None:
        """Return the normalized Telegram command, if the message has one."""

        if not self.text.startswith("/"):
            return None
        return self.text.split(maxsplit=1)[0].split("@", maxsplit=1)[0].lower()


def parse_message(update: dict[str, Any]) -> IncomingMessage | None:
    """Extract a text message from a Telegram update."""

    message = update.get("message")
    if not isinstance(message, dict):
        return None

    chat = message.get("chat")
    text = message.get("text")
    if not isinstance(chat, dict) or not isinstance(text, str):
        return None

    chat_id = chat.get("id")
    if not isinstance(chat_id, int):
        return None
    return IncomingMessage(chat_id=chat_id, text=text)


class TelegramClient:
    """Small Telegram Bot API client for polling and replies."""

    def __init__(self, token: str) -> None:
        if not token:
            raise ValueError("TELEGRAM_BOT_TOKEN is required")
        self.base_url = f"https://api.telegram.org/bot{token}"

    def send_message(self, chat_id: int, text: str) -> None:
        """Send a plain text message to a Telegram chat."""

        payload = urlencode({"chat_id": chat_id, "text": text}).encode("utf-8")
        request = Request(
            f"{self.base_url}/sendMessage",
            data=payload,
            method="POST",
        )
        with urlopen(request, timeout=10):
            return

    def get_updates(self, offset: int | None, timeout: int) -> list[dict[str, Any]]:
        """Fetch updates using Telegram long polling."""

        query = {"timeout": timeout}
        if offset is not None:
            query["offset"] = offset
        request = Request(f"{self.base_url}/getUpdates?{urlencode(query)}")
        with urlopen(request, timeout=timeout + 5) as response:
            payload = json.loads(response.read().decode("utf-8"))

        if not isinstance(payload, dict) or not payload.get("ok"):
            return []
        result = payload.get("result", [])
        return result if isinstance(result, list) else []
