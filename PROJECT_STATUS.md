# Zorqen Research - Project Status

> This file records verified repository reality for handoff between coding agents. It must be updated in every milestone commit. Git, tests, and implementation remain authoritative when this file is stale or incorrect.

## 1. Project Identity

- Product: Zorqen Research
- Repository: `ZavierAhmed/Zorqen-Research`
- Default branch: `main`
- Current branch: `main`
- Previous verified commit (Milestone 0.1A): `7fe8ee02c629df67ed9ec91c6a7c72455b925c1f`
- Milestone 0.2 base commit: `7fe8ee02c629df67ed9ec91c6a7c72455b925c1f`
- Milestone result commit: current HEAD containing this status update.
- Exact SHA: report after commit and record as the previous verified commit during the next status update.
- Master specification: `docs/specification/Zorqen_Research_Master_Specification_v0.1.pdf`
- Current environment: Windows development laptop
- Target deployment: Windows or Linux VPS
- Runtime principle: CPU-first; no mandatory GPU dependency
- Push state: confirm with `git status -sb` after commit (do not push unless instructed)

## 2. Product Purpose

Zorqen Research is a separate autonomous strategy-research and qualification platform. It will create controlled candidates, run deterministic testing and validation, apply hard gates and qualification scoring, and export qualified packages to MOMO Quant.

It does not connect to exchanges, place paper/live trades, approve live deployment, modify MOMO Quant, or use unrestricted strategy code generation in the MVP.

## 3. Initial Strategy Scope

### Primary

- Adaptive Multi-Timeframe Trend Breakout (`adaptive_mtf_trend_breakout`)
  - Stable UUID: `a1b2c3d4-e5f6-4789-a012-3456789abc01`

### Secondary

- Support and Resistance (`support_resistance`)
  - Stable UUID: `a1b2c3d4-e5f6-4789-a012-3456789abc02`

Registry metadata exists. Executable baseline behavior is not defined in Zorqen Research yet.

## 4. Current Milestone

- Milestone: `0.2` — Core Persistence, Audit Trail, and Strategy Family Registry
- Status: Complete pending independent review
- Objective: Shared SQLAlchemy foundation, strategy-family registry + seeds, append-only audit events, read-only APIs, Docker migrate service, full verification
- Implementation started: Yes
- Repository commit created: Yes (this milestone commit)

## 5. Latest Verified State

- Domain/application layers for strategy families and audit append
- Tables: `strategy_families`, `audit_events` via Alembic `0002_core_registry_and_audit`
- APIs: `GET /api/v1/strategy-families`, `GET /api/v1/strategy-families/{code}` (read-only)
- Docker: dedicated `migrate` service; API/worker wait for successful migration
- CI: quality, integration, docker-routing-smoke (extended with registry assertion)
- Frontend status page unchanged; routing regression still passing
- Tests: backend unit 25 + integration 9; frontend 15

## 6. Frozen Product Decisions

Unchanged. Research authority only; no paper/live trading; separate from MOMO Quant.

## 7. Architecture Direction

See `docs/adr/0001-foundation-stack.md` and `docs/adr/0002-core-registry-and-audit.md`.

## 8. Research Engine Status

- Campaign model: Not implemented
- Strategy DSL / executable definitions: Not implemented
- Data snapshots: Not implemented
- Backtest engine: Not implemented
- Validation: Not implemented
- Qualification policy: Not implemented
- Candidate packages: Not implemented
- MOMO Quant integration: Not implemented
- Strategy-family metadata registry: Implemented (Milestone 0.2)
- Audit-event append foundation: Implemented (no HTTP endpoint)

## 9. Outstanding Work

1. Independent review of Milestone 0.2
2. Authorize the next milestone from repository evidence
3. Formalize authoritative baselines for both strategies in later milestones

## 10. Known Risks / Limitations

- Database-level UPDATE/DELETE prevention for audit events is deferred; application-layer append-only is enforced and tested.
- Brief nginx 502s can occur while the API is still starting.
- GitHub Actions workflows were updated locally but not executed on GitHub in this session.
- No authentication yet.

## 11. Next Authorized Work

Awaiting independent review. **No later milestone is authorized.**

Do not implement strategy logic, backtesting, campaigns, candidates, scoring, MOMO Quant integration, or paper/live trading.

## 12. Coding-Agent Handoff

### Commands actually run for Milestone 0.2

```text
git rev-parse HEAD (start) -> 7fe8ee02c629df67ed9ec91c6a7c72455b925c1f
uv run ruff check . / ruff format --check . -> pass
uv run mypy src -> Success: no issues found in 34 source files
uv run pytest tests/unit -q -> 25 passed
uv run alembic upgrade head
uv run alembic downgrade 0001_baseline
uv run alembic upgrade head
uv run alembic downgrade base
uv run alembic upgrade head -> all succeeded
uv run pytest tests/integration -q -m integration -> 9 passed
uv run python -m zorqen_research.worker --check -> exit 0
frontend npm ci / lint / test --run / build -> 15 passed; build ok
docker compose config --quiet -> pass
docker compose down -v
docker compose build api worker frontend migrate
docker compose up -d postgres migrate api worker frontend
  migrate exited successfully after 0001+0002 upgrades
curl http://127.0.0.1:5173/api/v1/health/live -> healthy
curl http://127.0.0.1:5173/api/v1/health/ready -> ready / database healthy
curl http://127.0.0.1:5173/api/v1/strategy-families
  -> count=2; primary then secondary; both active; stable UUIDs
docker compose logs inspected (migrate upgrade, API 200s via nginx)
docker compose down -v
```

## 13. Change Log

| Date | Milestone | Commit | Summary | Verification |
|---|---|---|---|---|
| 2026-08-03 | Planning | `5276613` | Product direction and master specification v0.1 | Document-level only |
| 2026-08-03 | 0.1 | `34b85af` | Bootstrap executable repository foundation | 17 backend + 4 frontend |
| 2026-08-03 | 0.1A | `7fe8ee0` | Correct frontend API routing and Docker verification | 17 backend + 15 frontend; nginx smoke |
| 2026-08-03 | 0.2 | (this commit) | Core registry and audit persistence | 25 unit + 9 integration + 15 frontend; migrate+registry smoke |
