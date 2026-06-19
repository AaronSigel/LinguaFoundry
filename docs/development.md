# Development Guide

## Current State

LinguaFoundry is in scaffold state. There is no Python package metadata,
dependency lockfile, runnable service, or automated test suite yet.

## Local Setup

1. Clone the repository.
1. Copy `.env.example` to `.env` if local environment values are needed.
1. Add a virtual environment only when implementation code introduces Python
   dependencies.

## Running

No application entrypoint exists yet. When a service becomes runnable, document
the command in the service README and mirror the common path in the root
README.

## Testing and Quality

The scaffold CI installs `requirements-dev.txt` and runs these baseline gates:

- `mdformat --check .` for Markdown formatting.
- `ruff format --check .` and `ruff check .` when Python files exist.
- `pytest` when tests exist.
- `detect-secrets scan --all-files` with a failing check for potential committed
  secrets.

No application test suite exists yet. When code is added, prefer focused tests
close to the changed package or service. Document configured commands such as
`pytest`, `ruff`, formatting, and type checking before relying on them in
automation.

## Scope Rules

- Keep scaffold and documentation changes separate from feature work.
- Add dependencies only for code that uses them in the same change.
- Keep secrets out of Git; use `.env.example` for required variable names.
- Update `AGENTS.md` when agent workflow rules change.
