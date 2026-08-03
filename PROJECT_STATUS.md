# Zorqen Research - Project Status

> This file records verified repository reality for handoff between coding agents. It must be updated in every milestone commit. Git, tests, and implementation remain authoritative when this file is stale or incorrect.

## 1. Project Identity

- Product: Zorqen Research
- Repository: `ZavierAhmed/Zorqen-Research`
- Default branch: `main`
- Current branch: `main`
- Previous verified commit (Milestone 0.4A): `d541658d0ce51e9411576e106f726443aa70f7eb`
- Milestone 0.4B base commit: `d541658d0ce51e9411576e106f726443aa70f7eb`
- Milestone result commit: current HEAD containing this status update.
- Exact SHA: report after commit.
- Master specification: `docs/specification/Zorqen_Research_Master_Specification_v0.1.pdf`
- Current environment: Windows development laptop
- Target deployment: Windows or Linux VPS
- Runtime principle: CPU-first; no mandatory GPU dependency
- Push state: confirm with `git status -sb` after commit (do not push unless instructed)

## 2. Product Purpose

Unchanged. Public market-data import only; no account/trading APIs.

## 3. Initial Strategy Scope

Unchanged. Registry metadata only; executable baselines not defined.

## 4. Current Milestone

- Milestone: `0.4B` — Enforce Trade-Count and Artifact-Root Wiring Invariants
- Status: Complete pending independent review
- Base: `d541658d0ce51e9411576e106f726443aa70f7eb`
- Corrective defects closed:
  - `Candle.trade_count` accepts only real non-negative integers (rejects `bool` / float / Decimal / str)
  - Settings expose `artifact_root_configured` (`expanduser` only); store construction no longer resolves before symlink validation
- Implementation started: Yes
- Repository commit created: Yes (this milestone commit)

## 5. Latest Verified State

- Canonical trade_count invariant enforced in domain; Binance parser keeps sanitized `BinanceResponseError`
- CLI, dataset API routes, and tests pass `settings.artifact_root_configured` into `LocalFilesystemArtifactStore`
- Settings/store wiring tests cover symlink identity preservation and settings→store rejection
- Fixture and mocked import hashes unchanged

Fixture manifest hash:
`5a0f0d0aacc3bc06969c4d45a38906a8d8a423ab449178b22fbf6a8abe81df80`

Mocked 1005-candle import:
- normalized_sha256: `e54d56e814276e63574c57a66c6776bf3add0827c8401f354362695a34933159`
- content_hash: `ac9762134a0eb1f24b3dd9012df72f01ad19d4c1aa628188fcd6265195c3fc6e`

## 6–8. Product / Architecture / Research Engine

Corrective only. No candle-query API, resampling, strategies, backtesting, campaigns, candidates, scoring, MOMO, or trading.

## 9. Outstanding Work

Awaiting independent review of Milestone 0.4B.
No later milestone is authorized.

## 10. Verification Evidence (Milestone 0.4B)

Commands actually executed:

```text
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest tests/unit -q                                          # 177 passed
uv run pytest tests/integration/test_artifact_filesystem.py -q       # 9 passed
uv run pytest tests/integration -q -m integration                    # 29 passed
alembic upgrade/downgrade round-trip through 0002 and base           # OK
uv run zorqen-dataset publish-fixture                                # same fixture hash
uv run zorqen-dataset publish-fixture                                # idempotent
uv run python -m zorqen_research.worker --check                      # OK
frontend npm ci / lint / test / build                                # 15 tests
docker compose build (fixture + binance-import profiles)
docker compose up + fixture run + binance-import --help
curl.exe nginx health/live, ready, strategy-families, datasets
docker compose down -v
```

Live Binance: not rerun (no network behavior change).
GitHub Actions: unknown until push.

## 11. Known Defects and Limitations

Unchanged from Milestone 0.4A.

## 12. Next Authorized Work

None until Milestone 0.4B is independently accepted.
