# LinguaFoundry

LinguaFoundry is an open-source modular language learning platform with a
Telegram-first interface, SRS practice, and extensible language packs.

This repository is currently a scaffold for agent-assisted development. It
defines the intended package boundaries and baseline operating rules. The API
service includes an initial PostgreSQL database layer and Alembic migrations.

## Repository Layout

- `services/bot`: Telegram-facing entrypoint for the Stage 1 MVP.
- `services/api`: FastAPI backend skeleton with a health endpoint.
- `packages/core`: Shared domain logic, including SRS behavior.
- `packages/lang-packs`: Language content schemas and language packs.
- `docs`: Project documentation and development notes.

## Getting Started

1. Copy `.env.example` to `.env` for local configuration.
1. Read `AGENTS.md` before making automated changes.
1. Keep changes scoped to the relevant service, package, or documentation area.

CI quality gates install `requirements-dev.txt` and run Markdown formatting
checks, Python linting when Python files exist, tests when tests exist, and a
committed-secret scan.

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

Install API database dependencies and run migrations with:

```shell
python -m pip install -r services/api/requirements.txt
alembic -c services/api/alembic.ini upgrade head
```

Run the API service locally with:

```shell
python -m uvicorn services.api.app.main:app --reload
```

Run the Telegram bot lesson flow locally after setting `TELEGRAM_BOT_TOKEN`:

```sh
PYTHONPATH=packages/core:. python -m services.bot.app.main
```

Run the focused API tests with:

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
