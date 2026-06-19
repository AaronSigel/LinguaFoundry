# Agent Guidelines

These rules apply to automated and semi-automated development in this
repository.

## Scope Control

- Work only on the files required by the approved task.
- Preserve the existing monorepo layout unless a task explicitly changes it.
- Avoid unrelated refactors, dependency changes, and formatting churn.
- Treat `.env`, credentials, and local machine paths as private data.

## Repository Conventions

- Put Telegram-specific behavior in `services/bot`.
- Put future HTTP/API behavior in `services/api`.
- Put reusable domain logic in `packages/core`.
- Put language content structures and packs in `packages/lang-packs`.
- Put durable project guidance in `docs`.

## Verification

The repository currently has no runnable code, dependency file, or test command.
When implementation code is added, include the smallest useful verification
command in the relevant README and prefer standard Python tooling such as
`pytest`, `ruff`, and type checking when configured.

## Change Hygiene

- Keep commits focused and commit-ready.
- Do not edit generated artifacts unless the task requires it.
- Update `.env.example` when adding required configuration keys.
- Update documentation when adding a new service entrypoint, package interface,
  or developer command.
