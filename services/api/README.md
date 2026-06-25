# API Service

API service package for HTTP-facing behavior and durable storage.

## Database

The API database layer uses SQLAlchemy 2.x, asyncpg, PostgreSQL, and Alembic.
Configuration is read from environment variables:

- `DATABASE_URL`: PostgreSQL connection URL, using the
  `postgresql+asyncpg://` driver form.
- `DATABASE_ECHO`: set to `true` to log SQL statements locally.

Install API dependencies from the repository root:

```bash
python -m pip install -r services/api/requirements.txt
```

Run migrations from the repository root:

```bash
alembic -c services/api/alembic.ini upgrade head
```

Validate and import language packs from the repository root:

```bash
linguafoundry-lang-packs --check packages/lang-packs/examples
linguafoundry-lang-packs packages/lang-packs/examples
```

Create future migrations from SQLAlchemy model changes:

```bash
alembic -c services/api/alembic.ini revision --autogenerate -m "describe change"
```

Minimal ORM models live in `services/api/app/db/models.py` for users, lessons,
exercises, attempts, and per-user lesson progress.
FastAPI backend for LinguaFoundry HTTP endpoints.

## Structure

- `app/main.py`: application factory and ASGI app export.
- `app/config.py`: environment-backed runtime settings.
- `app/routers`: HTTP route modules.
- `app/dependencies.py`: dependency providers for future domain integration.
- `tests`: focused service tests.

## Configuration

The service reads shared repository settings from environment variables or a
local `.env` file:

- `APP_ENV`: runtime environment name, defaults to `development`.
- `LOG_LEVEL`: log verbosity, defaults to `INFO`.

## Run Locally

Install development dependencies, then run the ASGI app:

```sh
python -m uvicorn services.api.app.main:app --reload
```

The health endpoint is available at `GET /health`.

Learning workflow endpoints are available under `/learning`:

- `POST /learning/users`: register a learner.
- `GET /learning/lessons`: list published lessons.
- `POST /learning/sessions`: start or restart a lesson session.
- `GET /learning/sessions/{session_id}/exercise`: fetch the current exercise.
- `POST /learning/sessions/{session_id}/answers`: submit an answer.
- `GET /learning/users/{user_id}/sessions/active`: fetch active durable
  sessions for restart/resume flows.
- `GET /learning/users/{user_id}/progress`: fetch learner progress.
- `GET /learning/users/{user_id}/progress/stats`: fetch aggregate learner
  statistics.

Learning sessions are durable rows with the active exercise cursor and language
pack version used for the session. Progress rows remain aggregate per-lesson
state and should not be used as active session identifiers.

## Verification

Run the focused API tests with:

```sh
pytest services/api/tests
```
