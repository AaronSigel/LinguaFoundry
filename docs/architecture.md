# Architecture

LinguaFoundry is organized as a monorepo for a Telegram-first MVP.

The current repository state is intentionally documentation-first. Service and
package directories define ownership boundaries for future implementation.

## Services

- `services/bot`: Telegram-facing entrypoint for user interaction.
- `services/api`: Planned for a later stage and intentionally not implemented yet.

## Packages

- `packages/core`: Owns SRS and domain logic.
- `packages/lang-packs`: Owns the language content structure and language packs.

## Boundaries

- Bot orchestration should call reusable domain behavior from `packages/core`
  instead of duplicating learning logic.
- Language-specific lessons, prompts, or metadata should live under
  `packages/lang-packs`.
- The API service should not be introduced until an approved task defines its
  first endpoint and runtime requirements.
- Cross-cutting configuration keys must be reflected in `.env.example`.
