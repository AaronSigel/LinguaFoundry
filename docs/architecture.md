# Architecture

LinguaFoundry is organized as a monorepo for a Telegram-first MVP.

The current repository state is intentionally lightweight. Service and package
directories define ownership boundaries for implementation.

## Services

- `services/bot`: Telegram-facing entrypoint for user interaction.
- `services/api`: FastAPI backend skeleton with health checks and environment
  configuration.

## Packages

- `packages/core`: Owns SRS and domain logic.
- `packages/lang-packs`: Owns the language content structure and language packs.

## Boundaries

- Bot orchestration should call reusable domain behavior from `packages/core`
  instead of duplicating learning logic.
- Language-specific lessons, prompts, or metadata should live under
  `packages/lang-packs`.
- API routes should depend on reusable domain behavior through explicit
  dependency providers instead of coupling HTTP handlers to future package
  internals.
- Cross-cutting configuration keys must be reflected in `.env.example`.
