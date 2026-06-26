# Testing Guide

LinguaFoundry uses `pytest` for the current automated test suite. Install the
project and development dependencies from the repository root before running
tests:

```shell
python -m pip install -e .
python -m pip install -r requirements-dev.txt
```

## Full Suite

Run all tests from the repository root:

```shell
pytest
```

## Focused Suites

Use focused commands while working in one area:

```shell
pytest services/api/tests
pytest services/bot/tests
pytest packages/core/tests tests/core
```

The API MVP contract test verifies that the OpenAPI schema exposes the learner
route sequence, including the active-session resume and review-queue endpoints:

```shell
pytest services/api/tests/test_mvp_contract.py
```

The PostgreSQL MVP integration test applies Alembic migrations, imports the
Spanish A1 example pack, runs the learner workflow through the FastAPI routes,
and verifies persisted attempts, progress, durable session state, resume
behavior, and due-only review state after a new app instance is created. It is
skipped unless `TEST_DATABASE_URL` is set. Use a disposable PostgreSQL database
with a name ending in `_test`; the test refuses other database targets because
it drops and recreates schema. Include an explicit database user so local and CI
runs do not fall back to the current OS user:

```shell
TEST_DATABASE_URL=postgresql+asyncpg://linguafoundry@localhost:5432/linguafoundry_test pytest services/api/tests/test_mvp_integration.py
```

The language-pack tests validate committed example packs against the JSON Schema
and verify stable import identifiers:

```shell
pytest services/api/tests/test_lang_packs.py
```

## Quality Checks

Run the same local quality tools used by CI:

```shell
mdformat --check .
ruff format --check .
ruff check .
detect-secrets scan --all-files
```

Use formatter write mode before committing Markdown or Python formatting fixes:

```shell
mdformat .
ruff format .
```

## Manual Smoke Testing

The live MVP smoke path is documented in `docs/mvp-smoke-scenario.md`. Use it
when validating the Telegram bot against a real bot token, checking `/resume`
against active durable sessions, or verifying due review cards outside the
automated API integration path.
