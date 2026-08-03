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

## Current milestone scope

Milestone **0.1** established the executable repository foundation. Corrective milestone **0.1A** fixed frontend-to-API same-origin routing. Milestone **0.2** adds:

- Strategy-family metadata registry (two approved families, no executable definitions)
- Append-only application audit-event foundation
- Read-only strategy-family APIs
- Alembic migration `0002_core_registry_and_audit` with stable seed UUIDs
- Dedicated Docker Compose `migrate` service

**Still not implemented:** strategy logic/DSL, indicators, parameters, market-data import, backtesting, campaigns, candidates, scoring, worker job leasing, autonomous research, or MOMO Quant integration.

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
  api/             FastAPI routes and response schemas
  application/     Strategy-family and audit services
  domain/          Framework-independent values
  core/            Settings and logging
  infrastructure/  Database engine, models, repositories
  worker/          Worker entry point and idle service
frontend/          React + Vite + TypeScript UI
alembic/           Migrations (baseline + core registry/audit)
tests/unit|integration
docs/specification Master specification PDF
docs/adr           Architecture decision records
```

## Frontend API routing (same-origin default)

Ordinary local and Docker use must keep the browser on relative `/api/...` URLs. Do not set an absolute API URL for day-to-day development.

### Local Vite development

1. Browser requests `/api/v1/health/live` (same origin as the Vite app).
2. Vite proxies `/api` to `VITE_API_PROXY_TARGET` (default `http://127.0.0.1:8000`).
3. Leave `VITE_API_BASE_URL` empty in `frontend/.env`.

### Docker Compose / nginx

1. Browser requests `/api/v1/health/live` through the frontend origin (port 5173 by default).
2. nginx proxies `/api/` to `http://api:8000/api/`.
3. `VITE_API_BASE_URL` is a **build-time** Vite/Docker value. The Compose file does not pass it by default; the Dockerfile ARG defaults to empty so the production bundle uses relative `/api` requests.
4. A runtime Compose `environment:` value cannot change a compiled Vite bundle. To override intentionally:

```powershell
docker compose build --build-arg VITE_API_BASE_URL=https://api.example.com frontend
```

Do not put an absolute `VITE_API_BASE_URL` in the root `.env` for ordinary local or Docker use — that was the Milestone 0.1 routing defect.

Optional absolute `VITE_API_BASE_URL` overrides are supported for special deployments only. They are not the default and are not recommended for local or Compose use. This project does not add permissive CORS to paper over routing mistakes.

## Prerequisites

- Python 3.12
- [uv](https://docs.astral.sh/uv/)
- Node.js 20+ and npm
- PostgreSQL 16 (local install or Docker)
- Docker Desktop (optional, for Compose workflows)
- Git

## Environment configuration

Backend and Compose variables live at the repository root. Frontend Vite variables live under `frontend/`.

```powershell
Copy-Item .env.example .env
Copy-Item frontend\.env.example frontend\.env
```

### Root `.env` (backend / Compose)

- `ZORQEN_ENVIRONMENT`, `ZORQEN_LOG_LEVEL`
- `ZORQEN_API_HOST`, `ZORQEN_API_PORT`
- `ZORQEN_DATABASE_URL` (asyncpg)
- `ZORQEN_DATABASE_URL_SYNC` (psycopg, for Alembic)
- `ZORQEN_WORKER_IDLE_INTERVAL_SECONDS`
- `ZORQEN_ARTIFACT_ROOT`
- Optional Compose ports and Postgres credentials

Root `.env` does **not** automatically forward `VITE_API_BASE_URL` into the frontend image. An absolute frontend API base requires an explicit Docker build argument or an explicit Compose `build.args` entry. Ordinary local and Docker use leave the frontend base empty (same-origin `/api`).

### `frontend/.env` (Vite only)

- `VITE_API_PROXY_TARGET` — proxy destination for `npm run dev` (default `http://127.0.0.1:8000`)
- `VITE_API_BASE_URL` — leave empty so the browser uses relative `/api/...`

Vite loads env files from `frontend/`, not the repository root. Do not put Vite variables only in the root `.env` and expect the frontend to read them.

Do not commit `.env` files or real credentials.

## Windows PowerShell setup

```powershell
# From the repository root
uv sync --all-extras
Copy-Item .env.example .env
Copy-Item frontend\.env.example frontend\.env

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

# Frontend (separate terminal) — uses relative /api + Vite proxy
cd frontend
npm ci
npm run dev
```

## Linux / macOS setup

```bash
uv sync --all-extras
cp .env.example .env
cp frontend/.env.example frontend/.env
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

## Strategy-family metadata API

Read-only endpoints (metadata only — no strategy logic):

```http
GET /api/v1/strategy-families
GET /api/v1/strategy-families/{code}
```

Seeded families:

| Priority | Code | Display name |
|---|---|---|
| primary | `adaptive_mtf_trend_breakout` | Adaptive Multi-Timeframe Trend Breakout |
| secondary | `support_resistance` | Support and Resistance |

Executable baselines are not defined in Zorqen Research yet.

## Audit-event foundation

`audit_events` stores append-only application events (JSONB payload, correlation and entity indexes). Application code can append events; there is no HTTP audit API and no application update/delete path in this milestone. Ordinary read requests are not audited.

## Migrations

Direct (local PostgreSQL):

```powershell
uv run alembic upgrade head
uv run alembic downgrade 0001_baseline
uv run alembic upgrade head
uv run alembic downgrade base
uv run alembic upgrade head
```

Compose migration service (runs before API/worker):

```powershell
docker compose up -d postgres migrate
# or full stack:
docker compose up -d postgres migrate api worker frontend
```

The `migrate` service uses the backend image target `migrate`, runs `alembic upgrade head`, and exits. API and worker wait for `service_completed_successfully`.

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
uv run alembic downgrade 0001_baseline
uv run alembic upgrade head
uv run alembic downgrade base
uv run alembic upgrade head
```

## Docker commands

```powershell
docker compose config --quiet
docker compose build api worker frontend
docker compose up -d postgres migrate api worker frontend

# Verify through the frontend/nginx origin (not only port 8000):
curl.exe -f http://127.0.0.1:5173/api/v1/health/live
curl.exe -f http://127.0.0.1:5173/api/v1/health/ready
curl.exe -f http://127.0.0.1:5173/api/v1/strategy-families

docker compose logs --no-color postgres migrate api worker frontend
docker compose down -v
```

Unit tests do not require Docker. Integration tests and Alembic verification require a live PostgreSQL instance.

## Documentation

- Master specification: [docs/specification/Zorqen_Research_Master_Specification_v0.1.pdf](docs/specification/Zorqen_Research_Master_Specification_v0.1.pdf)
- Agent rules: [AGENTS.md](AGENTS.md)
- Verified project status: [PROJECT_STATUS.md](PROJECT_STATUS.md)
- Foundation ADR: [docs/adr/0001-foundation-stack.md](docs/adr/0001-foundation-stack.md)
- Registry/audit ADR: [docs/adr/0002-core-registry-and-audit.md](docs/adr/0002-core-registry-and-audit.md)

## Current non-goals

The following are explicitly out of scope and must not be started until authorized:

- Strategy logic (Adaptive MTF Trend Breakout, Support and Resistance)
- Backtesting and validation engines
- Candidate scoring and qualification policies
- Autonomous research loops
- Exchange connectivity or credentials
- Paper/live trading
- MOMO Quant API integration

## License

Proprietary — Zorqen / Zavier Ahmed. All rights reserved unless otherwise stated.
