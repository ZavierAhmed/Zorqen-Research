# Zorqen Research

Zorqen Research is a separate autonomous strategy-research and qualification application. It will eventually create controlled strategy candidates, run deterministic historical and validation tests, apply qualification gates, and export qualified packages to MOMO Quant.

## What it is not

Zorqen Research does **not**:

- Connect to exchange **account** or trading APIs
- Store trading credentials or API keys
- Place paper or live orders
- Approve its own production use
- Modify MOMO Quant
- Execute trades

It may fetch **public** market-data snapshots (Milestone 0.4) for research qualification only. Trading execution belongs to MOMO Quant.

## Current milestone scope

Milestone **0.1** established the executable repository foundation. Corrective milestone **0.1A** fixed frontend-to-API same-origin routing. Milestone **0.2** added the strategy-family registry and append-only audit trail. Milestone **0.3** / **0.3A** / **0.3B** added immutable artifacts and dataset manifests. Milestone **0.4** adds:

- Public Binance USDⓈ-M Futures kline import (no account, no API keys)
- Canonical immutable candle model and deterministic CSV serialization
- Strict UTC `[start, end)` ranges, closed-candle only, complete coverage
- Raw source-page artifacts, manifest version `2` provenance, idempotent CLI import
- Explicit Docker Compose profile `binance-import` (never started by `docker compose up`)

**Still not implemented:** candle-query API, live streams, resampling, Parquet, indicators, backtesting, strategies, campaigns, candidates, scoring, worker job leasing, autonomous research, or MOMO Quant integration.

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
  application/     Strategy-family, audit, dataset, market-data, and artifact workflows
  domain/          Framework-independent values (including candles)
  datasets/        Fixture + Binance import CLI (`zorqen-dataset`)
  core/            Settings and logging
  infrastructure/  Database, local artifact store, Binance public client, repositories
  worker/          Worker entry point and idle service
frontend/          React + Vite + TypeScript UI
alembic/           Migrations (baseline, registry/audit, dataset manifests)
tests/unit|integration|fixtures
docs/specification Master specification PDF
docs/adr           Architecture decision records
```

## Artifact storage and dataset manifests

PostgreSQL stores dataset **snapshot** and **partition** metadata only. Large files live in the local artifact store under `ZORQEN_ARTIFACT_ROOT` as SHA-256 content-addressed objects (`sha256/ab/cd/<digest>`).

Publication is atomic and **no-clobber**: bytes are written to a temp file, flushed, then linked into the final path with `os.link` (existing destinations are never replaced). Identical concurrent publishes reuse content; different bytes under the same key raise a sanitized collision error.

**Metadata rule:** first successfully persisted metadata wins (media type / original filename). Later publications do not replace it. `get_metadata` always verifies the stored record against actual object bytes. Missing metadata raises until a publish recovers it with no-clobber semantics.

**Orphans:** artifact objects may be written before a dataset DB commit. A rolled-back transaction can leave an unreferenced immutable object; that is harmless and reusable. There is no delete/GC API in this milestone.

Published artifacts have no overwrite/delete API. Store directories (`objects`, `meta`, `tmp`) must not be symlinks escaping the configured root.

Terminology:

| Term | Meaning |
|---|---|
| Snapshot | Named dataset version with status `draft` / `published` / `rejected` |
| Partition | One symbol+timeframe artifact belonging to a snapshot |
| Manifest | Canonical JSON describing a published snapshot and its partitions |

Supported research market (no exchange connectivity): `binance_futures`.

Approved symbols: `BTCUSDT`, `ETHUSDT`, `BNBUSDT`.

Approved timeframes: `1m`, `3m`, `5m`, `15m`, `30m`, `1h`, `4h`, `1d`, `1w` (aliases like `60m` / `H1` rejected).

### Fixture publication (explicit; not automatic on startup)

```powershell
uv run zorqen-dataset publish-fixture
# or:
uv run python -m zorqen_research.datasets publish-fixture
```

Idempotency: repeating the command with the same fixture content returns the existing published snapshot (`created=false`). A conflicting snapshot with the same name fails clearly. The fixture retains manifest version `1` and hash `5a0f0d0aacc3bc06969c4d45a38906a8d8a423ab449178b22fbf6a8abe81df80`.

Docker (after the stack is up):

```powershell
docker compose --profile fixture run --rm --no-deps dataset-fixture
```

### Binance public candle import (Milestone 0.4)

Imports historical **closed** USDⓈ-M Futures klines from the public REST host `https://fapi.binance.com` (`GET /fapi/v1/klines`). No Binance account, API key, API secret, signed request, or private endpoint is supported. The production origin is fixed in code (not configurable); tests inject an HTTP transport against that origin.

Supported symbols: `BTCUSDT`, `ETHUSDT`, `BNBUSDT`.

Supported timeframes: `1m`, `3m`, `5m`, `15m`, `30m`, `1h`, `4h`, `1d`, `1w` (aliases rejected).

Range semantics:

- Half-open interval `[start, end)` — `end` itself is not imported
- `start` and `end` must be timezone-aware UTC and exactly aligned to the timeframe
- `1d` aligns to `00:00:00 UTC`; `1w` aligns to Monday `00:00:00 UTC`
- Only fully closed candles are accepted (open-candle ranges are rejected, not clamped)
- Complete coverage is required; gaps/duplicates/out-of-order candles reject publication
- Guardrail: `ZORQEN_IMPORT_MAX_CANDLES` (default `100000`) rejects oversized expected counts before download

```powershell
uv run zorqen-dataset import-binance-klines `
  --symbol BTCUSDT `
  --timeframe 1h `
  --start 2026-06-01T00:00:00Z `
  --end 2026-06-02T00:00:00Z
```

JSON result on stdout includes `ok`, `created`, `snapshot_id`, `content_hash`, range fields, `candle_count`, `source_page_count`, and `normalized_sha256`.

Idempotency: the same import identity and logical content returns the existing snapshot (`created=false`). Same identity with different historical content raises a source-drift / duplicate conflict and does not replace the snapshot.

Artifacts:

- Raw successful Binance pages stored as immutable JSON objects (content-addressed keys only)
- Normalized partition is deterministic canonical CSV (`text/csv`, UTF-8, `\n` endings)
- Manifest version `2` includes provider/market/endpoint/symbol/timeframe/range provenance

Docker (stack must be up; this service never starts during ordinary `docker compose up`):

```powershell
docker compose --profile binance-import run --rm binance-import `
  import-binance-klines `
  --symbol BTCUSDT `
  --timeframe 1h `
  --start 2026-06-01T00:00:00Z `
  --end 2026-06-01T05:00:00Z
```

CI uses mocked HTTP transport only. An optional live public-data smoke check may be run manually when internet access is available; it is not part of GitHub Actions.

### Dataset read APIs

```http
GET /api/v1/datasets
GET /api/v1/datasets/{snapshot_id}
GET /api/v1/datasets/{snapshot_id}/manifest
```

Responses never include absolute filesystem paths. Draft/rejected snapshots are not listed. There is no create/upload/update/delete dataset HTTP API, no candle-query API, and no Binance download API.
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
uv run alembic downgrade 0002_core_registry_and_audit
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

The `migrate` service uses the backend image target `migrate`, runs `alembic upgrade head`, and exits. API and worker wait for `service_completed_successfully`. Migration `0003_dataset_manifest_foundation` creates `dataset_snapshots` and `dataset_partitions` (no fixture seed data).

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
uv run alembic downgrade 0002_core_registry_and_audit
uv run alembic upgrade head
uv run alembic downgrade base
uv run alembic upgrade head
```

## Docker commands

```powershell
docker compose config --quiet
docker compose build api worker migrate frontend
docker compose up -d postgres migrate api worker frontend

# Explicit fixture publish (not part of normal startup):
docker compose --profile fixture run --rm --no-deps dataset-fixture

# Verify through the frontend/nginx origin (not only port 8000):
curl.exe -f http://127.0.0.1:5173/api/v1/health/live
curl.exe -f http://127.0.0.1:5173/api/v1/health/ready
curl.exe -f http://127.0.0.1:5173/api/v1/strategy-families
curl.exe -f http://127.0.0.1:5173/api/v1/datasets

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
- Artifacts/datasets ADR: [docs/adr/0003-artifacts-and-dataset-manifests.md](docs/adr/0003-artifacts-and-dataset-manifests.md)

## Current non-goals

The following are explicitly out of scope and must not be started until authorized:

- Binance / network market-data downloading
- Candle-query API or candle tables in PostgreSQL
- Strategy logic (Adaptive MTF Trend Breakout, Support and Resistance)
- Backtesting and validation engines
- Candidate scoring and qualification policies
- Autonomous research loops
- Exchange connectivity or credentials
- Paper/live trading
- MOMO Quant API integration

## License

Proprietary — Zorqen / Zavier Ahmed. All rights reserved unless otherwise stated.
