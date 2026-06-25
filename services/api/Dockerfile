FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN addgroup --system app && adduser --system --ingroup app app

COPY pyproject.toml README.md ./
COPY packages ./packages
COPY services ./services

RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir .

USER app

CMD ["sh", "-c", "alembic -c services/api/alembic.ini upgrade head && if [ \"$SEED_LANG_PACKS\" = \"true\" ]; then linguafoundry-lang-packs $SEED_LANG_PACK_PATHS; fi && python -m uvicorn services.api.app.main:app --host 0.0.0.0 --port 8000"]
