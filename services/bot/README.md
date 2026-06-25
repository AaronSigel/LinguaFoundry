# Bot Service

Telegram-facing entrypoint for the Stage 1 MVP.

## Lesson Flow

The bot supports the API-backed MVP Telegram flow:

- `/start` verifies API reachability.
- `/lessons` lists published lessons from the backend API.
- `/lesson <lesson-slug-or-id>` starts a lesson session through the API and
  displays the first exercise.
- Plain text messages are submitted as answers to the active API session, then
  the bot returns the result and advances until the lesson is complete.
- `/review`, `/mistakes`, and `/repeat_errors` show missed exercises from the
  API review queue.

Run locally after setting `TELEGRAM_BOT_TOKEN`:

```sh
PYTHONPATH=packages/core:. python -m services.bot.app.main
```

Run focused tests with:

```sh
PYTHONPATH=packages/core:. pytest services/bot/tests
```

## Review Command

The Telegram adapter handles `/review`, `/mistakes`, and `/repeat_errors` by
calling `/learning/users/{user_id}/review`.

## Progress Command

`/progress` registers or resolves the Telegram learner through the backend API
and shows aggregate learning stats from `/learning/users/{user_id}/progress/stats`.

## Verification

From the repository root:

```sh
pytest services/bot/tests packages/core/tests/test_review.py
```

## Configuration

The bot reads configuration from environment variables or a local `.env` file:

- `TELEGRAM_BOT_TOKEN`: Telegram Bot API token.
- `API_BASE_URL`: backend API URL, defaults to `http://localhost:8000`.
- `API_KEY`: optional shared API key sent to protected backend API routes.
- `LOG_LEVEL`: structured log verbosity, defaults to `INFO`.
- `TELEGRAM_POLL_TIMEOUT`: Telegram long-polling timeout in seconds, defaults
  to `30`.
- `API_READY_TIMEOUT_SECONDS`: how long the bot waits for API readiness before
  exiting, defaults to `60`.
- `API_READY_INTERVAL_SECONDS`: delay between readiness attempts, defaults to
  `2`.

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
