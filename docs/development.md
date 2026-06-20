# Development Guide

## Current State

LinguaFoundry has a runnable Python baseline with a FastAPI API service,
Telegram bot service, shared core package, language-pack examples, PostgreSQL
models, and Alembic migrations. Python package metadata lives in
`pyproject.toml`; there is no dependency lockfile yet.

## Local Setup

1. Clone the repository.

1. Copy `.env.example` to `.env` if local environment values are needed.

1. Create a virtual environment and install the project when working on Python
   services:

   ```shell
   python -m pip install -e .
   python -m pip install -r requirements-dev.txt
   ```

## Running

Run the API service locally with:

```shell
python -m uvicorn services.api.app.main:app --reload
```

Run the Telegram bot locally after setting `TELEGRAM_BOT_TOKEN`:

```shell
python -m services.bot.app.main
```

Run PostgreSQL, API migrations, the API, and the bot through Docker Compose:

```shell
docker compose up
```

Service-specific commands should be documented in the relevant service README
and mirrored in the root README when they are common development paths.

## Testing and Quality

CI installs `requirements-dev.txt` and runs these baseline gates:

- `mdformat --check .` for Markdown formatting.
- `ruff format --check .` and `ruff check .` when Python files exist.
- `pytest` when tests exist.
- `detect-secrets scan --all-files` with a failing check for potential
  committed secrets.

See `docs/testing.md` for the focused test commands used by each package and
service.

Run the full test suite with:

```shell
pytest
```

Run the focused API tests with:

```shell
pytest services/api/tests
```

Run the MVP smoke contract test with:

```shell
pytest services/api/tests/test_mvp_smoke_contract.py
```

When more code is added, prefer focused tests close to the changed package or
service. Document configured commands such as `pytest`, `ruff`, formatting, and
type checking before relying on them in automation.

## Scope Rules

- Keep scaffold and documentation changes separate from feature work.
- Add dependencies only for code that uses them in the same change.
- Keep secrets out of Git; use `.env.example` for required variable names.
- Update `AGENTS.md` when agent workflow rules change.
