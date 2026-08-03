# Zorqen Research - Project Status

> This file records verified repository reality for handoff between coding agents. It must be updated in every milestone commit. Git, tests, and implementation remain authoritative when this file is stale or incorrect.

## 1. Project Identity

- Product: Zorqen Research
- Repository: `ZavierAhmed/Zorqen-Research`
- Default branch: `main`
- Current branch: `main`
- Previous verified commit (Milestone 0.3): `78423ca2058686416845703e68396cf638a71f6f`
- Milestone 0.3A base commit: `78423ca2058686416845703e68396cf638a71f6f`
- Milestone result commit: current HEAD containing this status update.
- Exact SHA: report after commit.
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

- Milestone: `0.3A` — Close Artifact Immutability and Metadata Verification Gaps
- Status: Complete pending independent review
- Base: `78423ca2058686416845703e68396cf638a71f6f`
- Corrective objective: no-clobber object/metadata publication, verified metadata, symlink containment, missing-metadata recovery; preserve Milestone 0.3 dataset behavior
- Implementation started: Yes
- Repository commit created: Yes (this milestone commit)

## 5. Latest Verified State

- Artifact store publishes via atomic hard-link no-clobber (`os.link`); destinations are never replaced
- First successfully persisted metadata wins; callers always reload verified metadata
- `get_metadata` verifies key/hash/size/media type/filename/timestamp against object bytes; missing metadata raises until publish recovers
- Symlink store dirs and nested escapes rejected
- Dataset fixture/APIs/migration `0003` / Docker fixture workflow unchanged from 0.3
- Manifest hash unchanged: `5a0f0d0aacc3bc06969c4d45a38906a8d8a423ab449178b22fbf6a8abe81df80`
- ADR 0003 amended for no-clobber, metadata rules, orphans, symlinks
- No later milestone is authorized

## 6. Frozen Product Decisions

Unchanged. Research authority only; no paper/live trading; separate from MOMO Quant.

## 7. Architecture Direction

See `docs/adr/0001-foundation-stack.md`, `docs/adr/0002-core-registry-and-audit.md`, and `docs/adr/0003-artifacts-and-dataset-manifests.md`.

## 8. Research Engine Status

- Campaign model: Not implemented
- Strategy DSL / executable definitions: Not implemented
- Data snapshots: Metadata + fixture foundation (0.3); artifact integrity hardened (0.3A); no network import
- Backtest engine: Not implemented
- Validation: Not implemented
- Qualification policy: Not implemented
- Candidate packages: Not implemented
- MOMO Quant integration: Not implemented
- Strategy-family metadata registry: Implemented (Milestone 0.2)
- Audit-event append foundation: Implemented
- Artifact store / dataset manifests: Implemented (0.3) and integrity-hardened (0.3A)

## 9. Outstanding Work

Awaiting independent review of Milestone 0.3A.
No later milestone is authorized.

## 10. Verification Evidence (Milestone 0.3A)

Commands actually executed on the development machine:

```text
uv sync --frozen --all-extras
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest tests/unit -q                                          # 60 passed
uv run pytest tests/integration/test_artifact_filesystem.py -q       # 8 passed
uv run alembic upgrade head / downgrade 0002 / upgrade head /
       downgrade base / upgrade head                                 # OK
uv run pytest tests/integration -q -m integration                    # 24 passed
uv run zorqen-dataset publish-fixture                                # created=true
uv run zorqen-dataset publish-fixture                                # created=false, same snapshot_id
uv run python -m zorqen_research.worker --check                      # OK
cd frontend && npm ci && npm run lint && npm run test -- --run && npm run build  # 15 tests
docker compose down -v / config / build / up
docker compose --profile fixture run --rm --no-deps dataset-fixture
curl nginx: health, strategy-families, datasets list/detail/manifest # OK
docker compose logs inspected; docker compose down -v
```

Manifest hash (unchanged):

`5a0f0d0aacc3bc06969c4d45a38906a8d8a423ab449178b22fbf6a8abe81df80`

GitHub Actions state: not observed (no push performed for this corrective milestone).

## 11. Known Defects and Limitations

- Fixture publication is explicit CLI/Compose only; normal startup does not seed datasets
- Artifact store is local filesystem only
- Object publication may precede DB commit; rolled-back transactions can leave unreferenced immutable orphans (harmless/reusable; no GC in this milestone)
- No candle-query or network market-data import
- Real symlink filesystem tests skip when the OS denies symlink creation; rejection logic remains unit-covered

## 12. Important Decisions

- No-clobber hard-link publication instead of `os.replace` for immutable objects and metadata
- First successfully persisted metadata wins for descriptive fields
- Missing metadata is an error on read; publish recovers with no-clobber create
- No later work (imports, candles, strategies, campaigns, MOMO, trading) is authorized
