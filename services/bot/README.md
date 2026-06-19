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
## Review Command

`services.bot.review` provides framework-agnostic handlers for the Telegram
mistake review command. `/review`, `/mistakes`, and `/repeat_errors` render the
learner's SRS-lite queue from `linguafoundry_core.review`.

## Verification

From the repository root:

```sh
pytest services/bot/tests packages/core/tests/test_review.py
```

## Configuration

The bot reads configuration from environment variables or a local `.env` file:

- `TELEGRAM_BOT_TOKEN`: Telegram Bot API token.
- `API_BASE_URL`: backend API URL, defaults to `http://localhost:8000`.
- `TELEGRAM_POLL_TIMEOUT`: Telegram long-polling timeout in seconds, defaults
  to `30`.

## Run Locally

Install repository dependencies, then run the polling entrypoint:

```sh
python -m services.bot.app.main
```

## Verification

Run the focused bot tests with:

```sh
pytest services/bot/tests
```
