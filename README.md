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
2. Read `AGENTS.md` before making automated changes.
3. Keep changes scoped to the relevant service, package, or documentation area.

No application run command is available in the scaffold state. CI quality gates
install `requirements-dev.txt` and run Markdown formatting checks, Python linting
when Python files exist, tests when tests exist, and a committed-secret scan.

Install API database dependencies and run migrations with:

```sh
python -m pip install -r services/api/requirements.txt
alembic -c services/api/alembic.ini upgrade head
```

Run the API service locally with:

```sh
python -m uvicorn services.api.app.main:app --reload
```

Run the Telegram bot lesson flow locally after setting `TELEGRAM_BOT_TOKEN`:

```sh
PYTHONPATH=packages/core:. python -m services.bot.app
```

Run the focused API tests with:

```sh
pytest services/api/tests
```

## Development Scope

- Prefer small, reviewed changes that preserve the monorepo boundaries.
- Do not introduce external services, secrets, or infrastructure without an approved task.
- Do not commit generated files, local virtual environments, or `.env` files.
- Keep public interfaces documented when adding package or service code.

## Documentation

- [Architecture](docs/architecture.md)
- [Development Guide](docs/development.md)
