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

The API smoke contract test verifies that the OpenAPI schema exposes the MVP
learner route sequence:

```shell
pytest services/api/tests/test_mvp_smoke_contract.py
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
when validating the API against PostgreSQL or validating the Telegram bot
against a real bot token. The automated smoke contract test does not replace a
live database and Telegram smoke run.
