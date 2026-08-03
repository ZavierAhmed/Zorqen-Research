# Zorqen Research - Project Status

> This file records verified repository reality for handoff between coding agents. It must be updated in every milestone commit. Git, tests, and implementation remain authoritative when this file is stale or incorrect.

## 1. Project Identity

- Product: Zorqen Research
- Repository: `ZavierAhmed/Zorqen-Research`
- Default branch: `main`
- Current branch: `main`
- Previous verified commit (Milestone 0.3B): `3e7221d20970b8d4d23493bf4dbb29237878c1e1`
- Milestone 0.4 base commit: `3e7221d20970b8d4d23493bf4dbb29237878c1e1`
- Milestone result commit: current HEAD containing this status update.
- Exact SHA: report after commit.
- Master specification: `docs/specification/Zorqen_Research_Master_Specification_v0.1.pdf`
- Current environment: Windows development laptop
- Target deployment: Windows or Linux VPS
- Runtime principle: CPU-first; no mandatory GPU dependency
- Push state: confirm with `git status -sb` after commit (do not push unless instructed)

## 2. Product Purpose

Zorqen Research is a separate autonomous strategy-research and qualification platform. It will create controlled candidates, run deterministic testing and validation, apply hard gates and qualification scoring, and export qualified packages to MOMO Quant.

It does not connect to exchange account/trading APIs, place paper/live trades, approve live deployment, modify MOMO Quant, or use unrestricted strategy code generation in the MVP. Public market-data import for research snapshots is allowed (Milestone 0.4).

## 3. Initial Strategy Scope

Unchanged. Registry metadata only; executable baselines not defined.

## 4. Current Milestone

- Milestone: `0.4` — Canonical Binance Futures Candle Import
- Status: Complete pending independent review
- Base: `3e7221d20970b8d4d23493bf4dbb29237878c1e1`
- Implementation started: Yes
- Repository commit created: Yes (this milestone commit)

## 5. Latest Verified State

- Public Binance USDⓈ-M Futures client (`https://fapi.binance.com`, `/fapi/v1/klines`) with allowlisted host
- No API key / secret / signed-request support
- Immutable canonical candle model (`Decimal`, UTC)
- Strict `[start, end)` alignment, closed-candle protection, `ZORQEN_IMPORT_MAX_CANDLES` (default 100000)
- Paginated retrieval (limit 1000), retries (429/`Retry-After`, terminal 418)
- Complete coverage / gap rejection; deterministic canonical CSV; raw JSON page artifacts
- Manifest version `2` import provenance; fixture remains version `1` with frozen hash
- Idempotent CLI `import-binance-klines`; Compose profile `binance-import`
- CI uses mocked HTTPX transport only; optional live smoke verified locally

Fixture manifest hash unchanged:
`5a0f0d0aacc3bc06969c4d45a38906a8d8a423ab449178b22fbf6a8abe81df80`

## 6–8. Product / Architecture / Research Engine

Market-data acquisition only. No candle-query API, resampling, indicators, strategies, backtesting, campaigns, candidates, scoring, worker leasing, autonomous research, MOMO integration, or trading.

## 9. Outstanding Work

Awaiting independent review of Milestone 0.4.
No later milestone is authorized.

## 10. Verification Evidence (Milestone 0.4)

Commands actually executed:

```text
uv sync --frozen --all-extras
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest tests/unit -q                                          # 88 passed
uv run pytest tests/integration/test_artifact_filesystem.py -q       # 9 passed
uv run pytest tests/integration -q -m integration                    # 29 passed
alembic upgrade/downgrade round-trip through 0002 and base           # OK
uv run zorqen-dataset publish-fixture                                # created=true
uv run zorqen-dataset publish-fixture                                # created=false, same hash
uv run python -m zorqen_research.worker --check                      # OK
frontend npm ci / lint / test / build                                # 15 tests
docker compose --profile fixture --profile binance-import build ...
docker compose up -d postgres migrate api worker frontend
docker compose --profile fixture run --rm --no-deps -T dataset-fixture
  -> manifest_hash=5a0f0d0aacc3bc06969c4d45a38906a8d8a423ab449178b22fbf6a8abe81df80
curl.exe nginx health/live, health/ready, strategy-families, datasets  # OK
docker compose --profile binance-import run --rm -T binance-import --help  # OK
```

Mocked multi-page import (1005 × 1h candles, page limit 1000):

```text
candle_count=1005
source_page_count=2
normalized_sha256=e54d56e814276e63574c57a66c6776bf3add0827c8401f354362695a34933159
content_hash=ac9762134a0eb1f24b3dd9012df72f01ad19d4c1aa628188fcd6265195c3fc6e
idempotent second import: created=false
source-drift / gap / audit-rollback / API exposure covered by integration tests
```

Optional live public Binance smoke (not CI):

```text
BTCUSDT 1h [2026-07-01T00:00:00Z, 2026-07-01T05:00:00Z)
first: created=true, candle_count=5, source_page_count=1
  content_hash=46a9b9b1f2d0f783bffe3ca2bb7d9c034ef24522f7d186e189fec3dc312359f8
  normalized_sha256=c342b5f595e49a4c8341241e57e3e57126c17eb2657d882d684c894d06c1d6d4
second: created=false, same snapshot_id and hashes
GET /api/v1/datasets returned the imported snapshot (manifest_version=2)
```

## 11. Known Defects and Limitations

- No candle-row query API
- No Parquet derivative
- No continuous ingestion / websockets
- Orphan content-addressed artifacts may remain after DB rollback (documented)

## 12. Next Authorized Work

None until Milestone 0.4 is independently accepted.
