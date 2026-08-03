# Zorqen Research - Project Status

> This file records verified repository reality for handoff between coding agents. It must be updated in every milestone commit. Git, tests, and implementation remain authoritative when this file is stale or incorrect.

## 1. Project Identity

- Product: Zorqen Research
- Repository: `ZavierAhmed/Zorqen-Research`
- Default branch: `main`
- Current branch: `main`
- Previous verified commit (Milestone 0.1): `34b85afcb7de96894a181a09b7a2705c9df93067`
- Milestone 0.1A base commit: `34b85afcb7de96894a181a09b7a2705c9df93067`
- Milestone result commit: current HEAD containing this status update.
- Exact SHA: report after commit and record as the previous verified commit during the next status update.
- Master specification: `docs/specification/Zorqen_Research_Master_Specification_v0.1.pdf`
- Current environment: Windows development laptop
- Target deployment: Windows or Linux VPS
- Runtime principle: CPU-first; no mandatory GPU dependency
- Push state at handoff writing: local `main` tracked `origin/main` (confirm with `git status -sb` after commit; this corrective commit is not pushed unless explicitly instructed)

## 2. Product Purpose

Zorqen Research is a separate autonomous strategy-research and qualification platform. It will create controlled candidates, run deterministic testing and validation, apply hard gates and qualification scoring, and export qualified packages to MOMO Quant.

It does not connect to exchanges, place paper/live trades, approve live deployment, modify MOMO Quant, or use unrestricted strategy code generation in the MVP.

## 3. Initial Strategy Scope

### Primary

- Adaptive Multi-Timeframe Trend Breakout

### Secondary

- Support and Resistance

Baseline behavior for both strategies must come from an authoritative implementation or explicitly approved formal definition before autonomous modification begins.

**Milestones 0.1 / 0.1A do not implement either strategy.**

## 4. Current Milestone

- Milestone: `0.1A` — Correct Frontend-to-API Routing and Close Deployment Verification Gap
- Status: Complete pending independent review
- Objective: Same-origin relative `/api` default for Vite and Docker/nginx; remove baked `http://127.0.0.1:8000` from production bundles; document env-file ownership; exercise real fetch URL tests; run full-stack Docker smoke
- Implementation started: Yes
- Repository commit created: Yes (this corrective milestone commit)

## 5. Defect Corrected

Milestone 0.1 frontend Dockerfile defaulted `VITE_API_BASE_URL=http://127.0.0.1:8000`, baking an absolute API origin into the static JS. Compose also exposed a runtime frontend `environment:` that cannot alter a compiled Vite bundle. Absolute browser calls to `:8000` are cross-origin; the API has no CORS. Required model is same-origin `/api` via Vite proxy (dev) or nginx → `api:8000` (Compose).

## 6. Latest Verified State

- Backend: unchanged health endpoints and worker foundation
- Frontend: `resolveApiBaseUrl` / `buildHealthUrl` / `fetchSystemStatus` default to relative `/api/...`
- Docker frontend image: `ARG VITE_API_BASE_URL=` (empty); no Compose build-arg by default
- nginx: `/api/` → `http://api:8000/api/` with forwarding headers
- Env model: root `.env.example` = backend/Compose; `frontend/.env.example` = Vite vars
- Tests: backend 17; frontend 15 (11 fetch/URL + 4 UI)
- CI: quality, integration, and new `docker-routing-smoke.yml`
- Docker full-stack smoke: passed through `http://127.0.0.1:5173/api/...`; production bundle contained no `127.0.0.1:8000`

### Files changed in 0.1A

- `frontend/src/api/status.ts`
- `frontend/src/api/status.test.ts` (new)
- `frontend/Dockerfile`
- `frontend/nginx.conf`
- `frontend/.env.example` (new)
- `frontend/.gitignore`
- `docker-compose.yml`
- `.env.example`
- `README.md`
- `.github/workflows/docker-routing-smoke.yml` (new)
- `PROJECT_STATUS.md`

## 7. Frozen Product Decisions

Unchanged from Milestone 0.1. Research authority only; no paper/live trading; separate from MOMO Quant.

## 8. Architecture Direction

Unchanged modular monolith. Routing decision: same-origin relative `/api` is the default; absolute `VITE_API_BASE_URL` is an intentional non-default override only.

## 9. Research Engine Status

- Campaign model: Not implemented
- Strategy DSL: Not implemented
- Data snapshots: Not implemented
- Backtest engine: Not implemented
- Validation: Not implemented
- Qualification policy: Not implemented
- Candidate packages: Not implemented
- MOMO Quant integration: Not implemented

## 10. Outstanding Work

1. Independent review of Milestone 0.1A
2. Authorize the next milestone from repository evidence
3. Formalize authoritative baselines for both strategies in later milestones

## 11. Known Risks / Limitations

- Early Compose startup can briefly return nginx 502 until the API process accepts connections; smoke waits until readiness succeeds.
- Postgres Alpine may log locale/`trust` auth warnings in local Compose; not treated as routing failures.
- GitHub Actions `docker-routing-smoke` was added but not executed on GitHub in this session.
- Worker/job leasing and research features remain deferred.

## 12. Next Authorized Work

Awaiting independent review. **Milestone 0.2 is not authorized.**

Do not implement strategy logic, backtesting, autonomous research, candidate scoring, MOMO Quant integration, or paper/live trading.

## 13. Coding-Agent Handoff

### Commands actually run for Milestone 0.1A

```text
git rev-parse HEAD (start) -> 34b85afcb7de96894a181a09b7a2705c9df93067
uv sync --frozen --all-extras
uv run ruff check . / ruff format --check . / mypy src -> pass
uv run pytest tests/unit -q -> 13 passed
uv run pytest tests/integration -q -m integration -> 4 passed
uv run alembic upgrade head / downgrade base / upgrade head -> pass
uv run python -m zorqen_research.worker --check -> exit 0
frontend: npm ci; npm run lint; npm run test -- --run -> 15 passed
frontend: npm run build -> pass
docker compose config --quiet -> pass
docker compose down -v
docker compose build api worker frontend
docker compose up -d postgres api worker frontend
curl http://127.0.0.1:5173/ -> 200
curl http://127.0.0.1:5173/api/v1/health/live -> healthy
curl http://127.0.0.1:5173/api/v1/health/ready -> ready / database healthy
production bundle grep for 127.0.0.1:8000 -> none
docker compose logs inspected (brief nginx 502 during API warm-up only)
docker compose down -v
```

## 14. Change Log

| Date | Milestone | Commit | Summary | Verification |
|---|---|---|---|---|
| 2026-08-03 | Planning | `5276613` | Product direction and master specification v0.1 | Document-level only |
| 2026-08-03 | 0.1 | `34b85af` | Bootstrap executable repository foundation | 17 backend + 4 frontend tests; Alembic; worker check; partial Docker |
| 2026-08-03 | 0.1A | (this commit) | Correct frontend API routing and Docker verification | 17 backend + 15 frontend tests; full Compose smoke via nginx `/api` |
