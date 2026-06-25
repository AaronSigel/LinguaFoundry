# LinguaFoundry

LinguaFoundry is an open-source modular language learning platform with a
Telegram-first interface, lesson practice, lightweight mistake review, and
extensible language packs.

The repository now contains a runnable baseline application:

- a FastAPI backend with health checks, learning workflow endpoints,
  PostgreSQL persistence, and Alembic migrations;
- a Telegram polling bot that lists lessons, runs lesson sessions, reports
  progress, and exposes review commands;
- shared core domain logic for lesson flow, progress, and review scheduling;
- example language packs and a JSON schema for content validation.

## Repository Layout

- `services/bot`: Telegram-facing entrypoint for the Stage 1 MVP.
- `services/api`: FastAPI backend with learning endpoints and database
  migrations.
- `packages/core`: Shared domain logic, including SRS behavior.
- `packages/lang-packs`: Language content schemas and language packs.
- `docs`: Project documentation and development notes.

## Getting Started

1. Create a virtual environment with Python 3.12 or newer.

1. Install the project and development tools:

   ```shell
   python -m pip install -e .
   python -m pip install -r requirements-dev.txt
   ```

1. Copy `.env.example` to `.env` for local configuration.

1. Read `AGENTS.md` before making automated changes.

1. Keep changes scoped to the relevant service, package, or documentation area.

CI quality gates install `requirements-dev.txt` and run Markdown formatting,
Python formatting, linting, tests, and a committed-secret scan.

## Docker Compose

Copy the environment template before starting the local stack:

```shell
cp .env.example .env
```

Set `TELEGRAM_BOT_TOKEN` in `.env` before starting the bot. The local stack uses
these variables:

- `TELEGRAM_BOT_TOKEN`: Telegram Bot API token required by `services/bot`.
- `API_BASE_URL`: host-side bot API URL for non-container runs.
- `TELEGRAM_POLL_TIMEOUT`: bot long-polling timeout in seconds.
- `APP_ENV`: runtime environment name.
- `LOG_LEVEL`: application log level.
- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`: PostgreSQL container
  credentials and database name.
- `POSTGRES_PORT`: host port mapped to PostgreSQL port `5432`.
- `API_PORT`: host port mapped to the API port `8000`.
- `DATABASE_URL`: host-side API database URL for non-container runs.
- `DATABASE_ECHO`: set to `true` to log SQL statements locally.
- `SEED_LANG_PACKS`: import example language packs during API container startup.
- `SEED_LANG_PACK_PATHS`: space-separated language pack files or directories
  imported when `SEED_LANG_PACKS` is true.

Start PostgreSQL, run API migrations, and launch the API and Telegram bot with:

```shell
docker compose up
```

Run only PostgreSQL and the API when a Telegram token is not available:

```shell
docker compose up db api
```

The API is available at `http://localhost:8000`, and PostgreSQL is available on
`localhost:5432` by default.

Check API readiness with:

```shell
curl http://localhost:8000/health
```

Install API database dependencies and run migrations with:

```shell
python -m pip install -r services/api/requirements.txt
alembic -c services/api/alembic.ini upgrade head
```

Validate and import example language packs with:

```shell
linguafoundry-lang-packs --check packages/lang-packs/examples
linguafoundry-lang-packs packages/lang-packs/examples
```

Run the API service locally with:

```shell
python -m uvicorn services.api.app.main:app --reload
```

Run the Telegram bot lesson flow locally after setting `TELEGRAM_BOT_TOKEN`:

```sh
PYTHONPATH=packages/core:. python -m services.bot.app.main
```

Run all automated tests with:

```shell
pytest
```

Run focused API tests with:

```shell
pytest services/api/tests
```

## Development Scope

- Prefer small, reviewed changes that preserve the monorepo boundaries.
- Do not introduce external services, secrets, or infrastructure without an
  approved task.
- Do not commit generated files, local virtual environments, or `.env` files.
- Keep public interfaces documented when adding package or service code.

## Documentation

- [Architecture](docs/architecture.md)
- [Development Guide](docs/development.md)
- [Future Backlog](docs/future-backlog.md)
- [Testing Guide](docs/testing.md)
- [MVP Smoke Scenario](docs/mvp-smoke-scenario.md)
- [Architecture Decision Records](docs/adr/README.md)
