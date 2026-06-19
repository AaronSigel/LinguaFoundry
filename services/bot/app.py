"""Minimal Telegram Bot API polling entrypoint."""

from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
from collections.abc import Iterator
from typing import Any

from services.bot.lesson_catalog import LessonCatalog
from services.bot.lesson_flow import TelegramLessonFlow

TELEGRAM_API_URL = "https://api.telegram.org"


def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required.")

    flow = TelegramLessonFlow(LessonCatalog.from_language_pack())
    offset = 0
    while True:
        for update in _get_updates(token, offset):
            offset = update["update_id"] + 1
            message = update.get("message", {})
            text = message.get("text")
            chat_id = message.get("chat", {}).get("id")
            if text is None or chat_id is None:
                continue
            reply = flow.handle_message(chat_id=chat_id, text=text)
            _send_message(token, reply.chat_id, reply.text)
        time.sleep(1)


def _get_updates(token: str, offset: int) -> Iterator[dict[str, Any]]:
    query = urllib.parse.urlencode({"timeout": 25, "offset": offset})
    with urllib.request.urlopen(  # noqa: S310 - Telegram API URL is fixed.
        f"{TELEGRAM_API_URL}/bot{token}/getUpdates?{query}",
        timeout=30,
    ) as response:
        payload = json.load(response)
    yield from payload.get("result", [])


def _send_message(token: str, chat_id: int, text: str) -> None:
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode()
    request = urllib.request.Request(
        f"{TELEGRAM_API_URL}/bot{token}/sendMessage",
        data=data,
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10):  # noqa: S310
        return


if __name__ == "__main__":
    main()
