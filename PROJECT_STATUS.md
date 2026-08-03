# Zorqen Research - Project Status

> This file records verified repository reality for handoff between coding agents. It must be updated in every milestone commit. Git, tests, and implementation remain authoritative when this file is stale or incorrect.

## 1. Project Identity

- Product: Zorqen Research
- Repository: `ZavierAhmed/Zorqen-Research`
- Default branch: `main`
- Current branch: `main`
- Base commit (Milestone 0.1 start): `5276613d1721a1baafe8b5602b24f4f5bece4d0f`
- Milestone result commit: current HEAD containing this status update.
- Exact SHA: report after commit and record as the previous verified commit during the next status update.
- Master specification: `docs/specification/Zorqen_Research_Master_Specification_v0.1.pdf`
- Current environment: Windows development laptop
- Target deployment: Windows or Linux VPS
- Runtime principle: CPU-first; no mandatory GPU dependency

## 2. Product Purpose

Zorqen Research is a separate autonomous strategy-research and qualification platform. It will create controlled candidates, run deterministic testing and validation, apply hard gates and qualification scoring, and export qualified packages to MOMO Quant.

It does not connect to exchanges, place paper/live trades, approve live deployment, modify MOMO Quant, or use unrestricted strategy code generation in the MVP.

## 3. Initial Strategy Scope

### Primary

- Adaptive Multi-Timeframe Trend Breakout

### Secondary

- Support and Resistance

Baseline behavior for both strategies must come from an authoritative implementation or explicitly approved formal definition before autonomous modification begins.

**Milestone 0.1 does not implement either strategy.**

## 4. Current Milestone

- Milestone: `0.1` — Repository Foundation and Executable Skeleton
- Status: Complete pending independent review
- Objective: Bootstrap executable API, worker, frontend, PostgreSQL/Alembic, tests, CI, Docker, and documentation
- Implementation started: Yes
- Repository commit created: Yes (this milestone commit)

## 5. Latest Verified State

- Backend: FastAPI app with `/api/v1/health/live`, `/api/v1/health/ready`, and root metadata
- Frontend: React + Vite + TypeScript system-status page
- Worker: Idle loop + `--check` mode
- Database: PostgreSQL via async SQLAlchemy + asyncpg; Alembic empty baseline `0001_baseline`
- Tests: Backend unit + integration; frontend Vitest component tests
- Migrations: Empty baseline only (no domain tables)
- CI: `.github/workflows/quality.yml` (ubuntu + windows) and `integration.yml` (PostgreSQL service)
- Docker: `docker-compose.yml` (postgres, api, worker, frontend) + Dockerfiles
- Build status: Verified locally (see commands below)

## 6. Frozen Product Decisions

- Umbrella brand: Zorqen
- New application: Zorqen Research
- Existing execution platform: MOMO Quant for now
- Future possible execution name: Zorqen Quant
- Separate repository, database, and deployment from MOMO Quant
- Initial strategy families: Adaptive MTF Trend Breakout and Support and Resistance
- Research authority only; no paper/live trading
- Candidate-package file integration before API integration
- One master PDF plus `AGENTS.md` and this status file
- Milestone-based coding with loop prompting and independent review after every commit

## 7. Architecture Direction

Implemented foundation stack (see `docs/adr/0001-foundation-stack.md`):

- Python 3.12 + uv
- FastAPI and Pydantic v2 / pydantic-settings
- PostgreSQL and Alembic
- Separate Python worker process (job leasing deferred)
- React, Vite, and TypeScript
- pytest, pytest-asyncio, HTTPX, Vitest, React Testing Library
- Ruff and mypy (strict)
- Docker Compose plus direct Windows commands
- Filesystem artifact root placeholder via `ZORQEN_ARTIFACT_ROOT`

## 8. Research Engine Status

- Campaign model: Not implemented
- Strategy DSL: Not implemented
- Data snapshots: Not implemented
- Backtest engine: Not implemented
- Validation: Not implemented
- Qualification policy: Not implemented
- Candidate packages: Not implemented
- MOMO Quant integration: Not implemented

## 9. Outstanding Work

1. Independent review of Milestone 0.1
2. Authorize the next milestone from repository evidence
3. Formalize authoritative baselines for both strategies in later milestones
4. Later: job leasing, research campaigns, evaluators, exports

## 10. Known Risks / Limitations

- Baseline strategy logic has not yet been imported or formalized.
- Final qualification thresholds require calibration.
- AI model/provider for structural hypothesis generation is not selected.
- MOMO Quant import API is not designed.
- Worker is idle-only; no job processing exists yet.
- Docker image builds for api/worker/frontend: API image build verified locally (`docker compose build api`). Worker/frontend image builds were not separately smoke-tested in this session; Compose config validates all services.

## 11. Next Authorized Work

Awaiting independent review. **No later milestone is authorized.**

Do not implement strategy logic, backtesting, autonomous research, candidate scoring, MOMO Quant integration, or paper/live trading.

## 12. Coding-Agent Handoff

A future coding agent must read:

1. `README.md`
2. `AGENTS.md`
3. `PROJECT_STATUS.md`
4. Active milestone prompt
5. Git status, branch, recent log, and diff
6. Relevant tests
7. Relevant implementation files

### Commands actually run for Milestone 0.1 verification

Initial inspection:

```text
git status  -> clean on main at 5276613d1721a1baafe8b5602b24f4f5bece4d0f
git branch --show-current -> main
git rev-parse HEAD -> 5276613d1721a1baafe8b5602b24f4f5bece4d0f
```

Python / backend:

```text
uv sync --all-extras --python 3.12
uv run ruff check .                  -> All checks passed
uv run ruff format --check .         -> 33 files already formatted
uv run mypy src                      -> Success: no issues found in 16 source files
uv run pytest tests/unit tests/integration -q
  -> 17 passed
uv run alembic upgrade head
uv run alembic downgrade base
uv run alembic upgrade head          -> all succeeded against Docker PostgreSQL
uv run python -m zorqen_research.worker --check
  -> exit 0, "PostgreSQL is reachable"
Worker --check against unreachable DB
  -> exit 1, "PostgreSQL is unavailable"
```

Frontend (`frontend/`):

```text
npm ci / npm install
npm run lint                         -> passed
npm run test -- --run                -> 4 passed
npm run build                        -> vite production build succeeded
```

Docker:

```text
docker compose up -d postgres        -> healthy
docker compose config                -> valid (no errors)
docker compose build api             -> succeeded
Docker Desktop available: yes (Docker 29.6.1 / Compose v5.1.4)
```

CI files created:

- `.github/workflows/quality.yml`
- `.github/workflows/integration.yml`

## 13. Change Log

| Date | Milestone | Commit | Summary | Verification |
|---|---|---|---|---|
| 2026-08-03 | Planning | `5276613` | Product direction and master specification v0.1 established | Document-level only |
| 2026-08-03 | 0.1 | (this commit) | Bootstrap executable repository foundation | 17 backend + 4 frontend tests; Alembic round-trip; worker check; Docker postgres + compose config |
