# Architecture

LinguaFoundry is organized as a monorepo for a Telegram-first MVP.

## Services

- `services/bot`: Telegram-facing entrypoint for user interaction.
- `services/api`: Planned for a later stage and intentionally not implemented yet.

## Packages

- `packages/core`: Owns SRS and domain logic.
- `packages/lang-packs`: Owns the language content structure and language packs.
