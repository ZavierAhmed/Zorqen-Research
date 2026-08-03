# Zorqen Research - Project Status

> This file records verified repository reality for handoff between coding agents. It must be updated in every milestone commit. Git, tests, and implementation remain authoritative when this file is stale or incorrect.

## 1. Project Identity

- Product: Zorqen Research
- Repository: `ZavierAhmed/Zorqen-Research`
- Default branch: `main`
- Current branch: `main`
- Previous verified commit (Milestone 0.2): `f7a8064654873a234b078d1fbc6bffd1c5e1d79f`
- Milestone 0.3 base commit: `f7a8064654873a234b078d1fbc6bffd1c5e1d79f`
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

- Milestone: `0.3` — Immutable Artifact Storage and Dataset Manifest Foundation
- Status: Complete pending independent review
- Objective: Local content-addressed artifact store, dataset snapshot/partition metadata, canonical manifests, fixture CLI, read-only dataset APIs, migration `0003`, Docker/CI verification
- Implementation started: Yes
- Repository commit created: Yes (this milestone commit)

## 5. Latest Verified State

- Local SHA-256 content-addressed artifact store under `ZORQEN_ARTIFACT_ROOT` (atomic publish, no overwrite/delete API)
- Tables: `dataset_snapshots`, `dataset_partitions` via Alembic `0003_dataset_manifest_foundation`
- Canonical market `binance_futures`; symbols `BTCUSDT`/`ETHUSDT`/`BNBUSDT`; timeframes `1m`…`1w`
- Fixture CLI: `uv run zorqen-dataset publish-fixture` (idempotent on identical logical content)
- APIs: `GET /api/v1/datasets`, `GET /api/v1/datasets/{id}`, `GET /api/v1/datasets/{id}/manifest`
- Audit: `dataset_snapshot.published` appends in the same DB transaction; nested non-JSON payloads rejected
- Docker: `dataset-fixture` Compose profile one-shot; artifact volume shared by API/worker
- CI docker-routing-smoke extended with fixture publish + dataset nginx checks
- ADR: `docs/adr/0003-artifacts-and-dataset-manifests.md`
- Tests (this verification pass): backend unit 53 + integration 19; frontend 15
- Not implemented: Binance download, candle-query API, backtester, strategies, campaigns, candidates, MOMO

## 6. Frozen Product Decisions

Unchanged. Research authority only; no paper/live trading; separate from MOMO Quant.

## 7. Architecture Direction

See `docs/adr/0001-foundation-stack.md`, `docs/adr/0002-core-registry-and-audit.md`, and `docs/adr/0003-artifacts-and-dataset-manifests.md`.

## 8. Research Engine Status

- Campaign model: Not implemented
- Strategy DSL / executable definitions: Not implemented
- Data snapshots: Metadata + fixture foundation implemented (Milestone 0.3); no network import
- Backtest engine: Not implemented
- Validation: Not implemented
- Qualification policy: Not implemented
- Candidate packages: Not implemented
- MOMO Quant integration: Not implemented
- Strategy-family metadata registry: Implemented (Milestone 0.2)
- Audit-event append foundation: Implemented (hardened JSON payload validation in 0.3)
- Artifact store / dataset manifests: Implemented (Milestone 0.3)

## 9. Outstanding Work

Authorized next milestone work only (not started): market-data import beyond fixtures, candle tooling, strategies, campaigns, etc., per product roadmap.

## 10. Verification Evidence (Milestone 0.3)

Commands actually executed on the development machine:

```text
uv sync --frozen --all-extras
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest tests/unit -q                          # 53 passed
uv run pytest tests/integration -q -m integration    # 19 passed
uv run alembic upgrade head
uv run alembic downgrade 0002_core_registry_and_audit
uv run alembic upgrade head
uv run alembic downgrade base
uv run alembic upgrade head
uv run zorqen-dataset publish-fixture                # created=true
uv run zorqen-dataset publish-fixture                # created=false (idempotent)
uv run python -m zorqen_research.worker --check
cd frontend && npm ci && npm run lint && npm run test -- --run && npm run build  # 15 tests
docker compose down -v
docker compose config --quiet
docker compose build api worker migrate frontend
docker compose up -d postgres migrate api worker frontend
docker compose --profile fixture run --rm --no-deps dataset-fixture
curl through nginx: health live/ready, strategy-families, datasets list/detail/manifest
docker compose logs --no-color postgres migrate api worker frontend
docker compose down -v
```

Manifest hash observed for the packaged BTCUSDT 1h fixture:

`5a0f0d0aacc3bc06969c4d45a38906a8d8a423ab449178b22fbf6a8abe81df80`

GitHub Actions state: not observed from this machine after push (no push performed for this milestone).

## 11. Known Defects and Limitations

- Fixture publication is explicit CLI/Compose only; normal startup does not seed datasets
- Artifact store is local filesystem only
- No candle-query or network market-data import
- Application-level published immutability; DB role revoke of UPDATE is deferred

## 12. Important Decisions

- Large candle bytes stay out of PostgreSQL; metadata references content-addressed artifact keys
- Manifest `content_hash` covers logical content (excludes snapshot id and publication timestamp) so fixture republication is idempotent
- `.gitignore` uses `/artifacts/` so the Python package `infrastructure/artifacts` is tracked
