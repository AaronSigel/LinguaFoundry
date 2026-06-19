# Bot Service

Telegram-facing entrypoint for the Stage 1 MVP.

## Lesson Flow

The bot supports a dependency-free Telegram polling flow:

- `/start` or `/lessons` lists available lessons from the bundled example
  language pack.
- `/lesson <lesson-id>` starts a lesson and displays the first exercise.
- Plain text messages are treated as answers, then the bot returns the result
  and advances to the next exercise until the lesson is complete.

Run locally after setting `TELEGRAM_BOT_TOKEN`:

```sh
PYTHONPATH=packages/core:. python -m services.bot.app
```

Run focused tests with:

```sh
PYTHONPATH=packages/core:. pytest services/bot/tests
```
