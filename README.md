# Zorqen Research

Zorqen Research is a separate autonomous strategy-research and qualification application. It will eventually create controlled strategy candidates, run deterministic historical and validation tests, apply qualification gates, and export qualified packages to MOMO Quant.

## What it is not

Zorqen Research does **not**:

- Connect to exchanges
- Store trading credentials
- Place paper or live orders
- Approve its own production use
- Modify MOMO Quant
- Execute trades

Trading execution belongs to MOMO Quant. This repository is research and qualification only.

## Current milestone scope (0.1)

Milestone 0.1 establishes the executable repository foundation only:

- Python 3.12 FastAPI backend with liveness/readiness probes
- Separate Python worker entry point with `--check` mode
- PostgreSQL connectivity and Alembic migrations (empty baseline)
- React + Vite + TypeScript system-status frontend
- Docker Compose development support
- Backend and frontend automated tests
- GitHub Actions quality and integration workflows
- Documentation and architecture decision records

**Not implemented yet:** strategy generation, backtesting, candidate scoring, autonomous research loops, or MOMO Quant integration.

## Architecture overview

Modular monolith with separate processes:

| Process | Role |
|---|---|
| API | FastAPI HTTP service (`zorqen_research.api`) |
| Worker | Independent idle process (`python -m zorqen_research.worker`) |
| Frontend | React operator UI under `frontend/` |
| PostgreSQL | System of record |

```text
src/zorqen_research/
  api/             FastAPI app and health routes
  core/            Settings and logging
  infrastructure/  Database engine and metadata
  worker/          Worker entry point and idle service
frontend/          React + Vite + TypeScript UI
alembic/           Migrations (empty baseline in 0.1)
tests/unit|integration
docs/specification Master specification PDF
docs/adr           Architecture decision records
```

## Prerequisites

- Python 3.12
- [uv](https://docs.astral.sh/uv/)
- Node.js 20+ and npm
- PostgreSQL 16 (local install or Docker)
- Docker Desktop (optional, for Compose workflows)
- Git

## Environment configuration

Copy the example file and adjust values:

```powershell
Copy-Item .env.example .env
```

All backend settings use the `ZORQEN_` prefix. See `.env.example` for:

- `ZORQEN_ENVIRONMENT`, `ZORQEN_LOG_LEVEL`
- `ZORQEN_API_HOST`, `ZORQEN_API_PORT`
- `ZORQEN_DATABASE_URL` (asyncpg)
- `ZORQEN_DATABASE_URL_SYNC` (psycopg, for Alembic)
- `ZORQEN_WORKER_IDLE_INTERVAL_SECONDS`
- `ZORQEN_ARTIFACT_ROOT`
- `VITE_API_BASE_URL` (frontend)

Do not commit `.env` or real credentials.

## Windows PowerShell setup

```powershell
# From the repository root
uv sync --all-extras
Copy-Item .env.example .env

# Start PostgreSQL (Docker example)
docker compose up -d postgres

# Apply migrations
uv run alembic upgrade head

# API
uv run uvicorn zorqen_research.api.app:create_app --factory --host 127.0.0.1 --port 8000

# Worker (separate terminal)
uv run python -m zorqen_research.worker
# or one-shot check:
uv run python -m zorqen_research.worker --check

# Frontend (separate terminal)
cd frontend
npm ci
npm run dev
```

## Linux / macOS setup

```bash
uv sync --all-extras
cp .env.example .env
docker compose up -d postgres
uv run alembic upgrade head
uv run uvicorn zorqen_research.api.app:create_app --factory --host 127.0.0.1 --port 8000
uv run python -m zorqen_research.worker --check
cd frontend && npm ci && npm run dev
```

## PostgreSQL

Docker Compose provides PostgreSQL with a health check and persistent volume:

```powershell
docker compose up -d postgres
docker compose ps
```

Default development credentials in `.env.example` are local placeholders (`zorqen` / `zorqen`), not production secrets.

## Test commands

### Backend

```powershell
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest tests/unit -q
uv run pytest tests/integration -q -m integration
```

### Frontend

```powershell
cd frontend
npm ci
npm run lint
npm run test -- --run
npm run build
```

### Alembic round-trip (requires PostgreSQL)

```powershell
uv run alembic upgrade head
uv run alembic downgrade base
uv run alembic upgrade head
```

## Docker commands

```powershell
docker compose config
docker compose up -d postgres
docker compose up --build api worker frontend
```

Unit tests do not require Docker. Integration tests and Alembic verification require a live PostgreSQL instance.

## Documentation

- Master specification: [docs/specification/Zorqen_Research_Master_Specification_v0.1.pdf](docs/specification/Zorqen_Research_Master_Specification_v0.1.pdf)
- Agent rules: [AGENTS.md](AGENTS.md)
- Verified project status: [PROJECT_STATUS.md](PROJECT_STATUS.md)
- Foundation ADR: [docs/adr/0001-foundation-stack.md](docs/adr/0001-foundation-stack.md)

## Current non-goals

The following are explicitly out of scope for Milestone 0.1 and must not be started until authorized:

- Strategy logic (Adaptive MTF Trend Breakout, Support and Resistance)
- Backtesting and validation engines
- Candidate scoring and qualification policies
- Autonomous research loops
- Exchange connectivity or credentials
- Paper/live trading
- MOMO Quant API integration

## License

Proprietary — Zorqen / Zavier Ahmed. All rights reserved unless otherwise stated.
