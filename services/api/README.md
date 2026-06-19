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

Create future migrations from SQLAlchemy model changes:

```bash
alembic -c services/api/alembic.ini revision --autogenerate -m "describe change"
```

Minimal ORM models live in `services/api/app/db/models.py` for users, lessons,
exercises, attempts, and per-user lesson progress.
