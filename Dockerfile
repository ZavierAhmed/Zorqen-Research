# syntax=docker/dockerfile:1

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.12.1 /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock README.md ./
COPY src ./src
COPY alembic ./alembic
COPY alembic.ini ./

RUN uv sync --frozen --no-dev

FROM base AS migrate
CMD ["uv", "run", "alembic", "upgrade", "head"]

FROM base AS api
EXPOSE 8000
CMD ["uv", "run", "uvicorn", "zorqen_research.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]

FROM base AS worker
CMD ["uv", "run", "python", "-m", "zorqen_research.worker"]
