# Architecture

LinguaFoundry is organized as a Python monorepo for a Telegram-first MVP. The
current baseline keeps user interaction, HTTP persistence, reusable domain
logic, and language content in separate ownership areas so each surface can
evolve independently.

## Runtime Shape

The baseline application has two service entrypoints:

- `services/api/app/main.py` exports the FastAPI application used by local
  development, Docker Compose, and tests.
- `services/bot/app/main.py` runs the Telegram long-polling bot and connects it
  to the API through `services.bot.app.api_client.ApiClient`.

PostgreSQL is the durable store for the API. SQLAlchemy models and Alembic
migrations define the initial schema for learners, lessons, exercises,
attempts, and progress.

## Services

- `services/bot`: Telegram-facing entrypoint for user interaction. The bot owns
  Telegram transport concerns, command routing, and learner-facing message
  rendering.
- `services/api`: FastAPI backend with health checks, learning workflow
  endpoints, environment configuration, database access, and migrations.

## Packages

- `packages/core`: Owns reusable learning-session, progress, and review logic.
  It must not depend on Telegram, FastAPI, SQLAlchemy, or file storage.
- `packages/lang-packs`: Owns language content structures, JSON schema, and
  example packs.

## Data Flow

1. A learner interacts with the Telegram bot.
1. The bot registers or resolves the learner through the API.
1. The bot requests lessons, starts sessions, submits answers, and fetches
   progress through `/learning` endpoints.
1. The API persists learners, lesson state, attempts, and progress in
   PostgreSQL.
1. Shared package code remains available for service behavior that should be
   independent of transport or persistence.

## Boundaries

- Bot orchestration should call reusable domain behavior from `packages/core`
  instead of duplicating learning logic.
- Language-specific lessons, prompts, or metadata should live under
  `packages/lang-packs`.
- API-specific database configuration, SQLAlchemy models, and migrations live
  under `services/api`.
- Cross-cutting configuration keys must be reflected in `.env.example`.

## Deployment and Operations

Docker Compose is the local integration path for PostgreSQL, API migrations,
the API service, and the Telegram bot. The API can also run directly with
`python -m uvicorn services.api.app.main:app --reload`; the bot can run
directly with `python -m services.bot.app.main` once `TELEGRAM_BOT_TOKEN` is
configured.
