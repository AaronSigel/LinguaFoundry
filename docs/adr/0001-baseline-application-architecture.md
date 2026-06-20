# ADR-0001: Baseline Application Architecture

## Status

Accepted

## Context

LinguaFoundry now has a working baseline application rather than only a
directory scaffold. The baseline includes a Telegram-facing bot, a FastAPI API,
PostgreSQL persistence through SQLAlchemy and Alembic, reusable learning-domain
code, and language-pack examples with a JSON schema.

The project needs a documented architecture decision that preserves the
monorepo boundaries as more learner flows, content, and persistence behavior
are added.

## Decision

Keep the baseline architecture split across these areas:

- `services/bot` owns Telegram polling, command handling, learner-facing text,
  and API client integration.
- `services/api` owns HTTP endpoints, environment-backed API configuration,
  database sessions, SQLAlchemy models, and Alembic migrations.
- `packages/core` owns transport-independent learning, progress, and review
  domain logic.
- `packages/lang-packs` owns content schemas and bundled language-pack
  examples.
- `docs` owns durable project guidance, smoke scenarios, testing notes, and
  ADRs.

The API remains the durable persistence boundary for learner state. The bot
integrates with the API instead of reaching into API database internals.

## Consequences

Service code can change transport or persistence details without forcing
language-pack or core-domain rewrites. The bot can stay focused on Telegram UX,
while the API remains the source of truth for learner progress and attempts.

Changes that cross these boundaries need matching documentation updates and, if
they alter a long-term architectural choice, a new ADR.

## Links

- Related issues: TASK-0022
- Related pull requests:
