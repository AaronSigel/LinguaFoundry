# Bot Service

Telegram-facing entrypoint for the Stage 1 MVP.

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
