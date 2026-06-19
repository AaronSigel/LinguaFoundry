# API Service

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

## Verification

Run the focused API tests with:

```sh
pytest services/api/tests
```
