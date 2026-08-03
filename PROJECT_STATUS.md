# Zorqen Research - Project Status

> This file records verified repository reality for handoff between coding agents. It must be updated in every milestone commit. Git, tests, and implementation remain authoritative when this file is stale or incorrect.

## 1. Project Identity

- Product: Zorqen Research
- Repository: `ZavierAhmed/Zorqen-Research`
- Default branch: `main`
- Current branch: `main`
- Previous verified commit (Milestone 0.4): `dffd667c26216ebf1878e55e6abe72dde70b45c1`
- Milestone 0.4A base commit: `dffd667c26216ebf1878e55e6abe72dde70b45c1`
- Milestone result commit: current HEAD containing this status update.
- Exact SHA: report after commit.
- Master specification: `docs/specification/Zorqen_Research_Master_Specification_v0.1.pdf`
- Current environment: Windows development laptop
- Target deployment: Windows or Linux VPS
- Runtime principle: CPU-first; no mandatory GPU dependency
- Push state: confirm with `git status -sb` after commit (do not push unless instructed)

## 2. Product Purpose

Unchanged from Milestone 0.4. Public market-data import only; no account/trading APIs.

## 3. Initial Strategy Scope

Unchanged. Registry metadata only; executable baselines not defined.

## 4. Current Milestone

- Milestone: `0.4A` — Enforce Binance Client Boundaries and Canonical Candle Invariants
- Status: Complete pending independent review
- Base: `dffd667c26216ebf1878e55e6abe72dde70b45c1`
- Corrective defects closed:
  - Application owns `MarketDataClient`; import service no longer types against the concrete HTTPX client
  - Production origin fixed to exact `https://fapi.binance.com` (no public `base_url`, no `.binance.local`)
  - Canonical candles reject non-UTC offsets and non-finite Decimals; parser sanitizes non-finite rows
- Implementation started: Yes
- Repository commit created: Yes (this milestone commit)

## 5. Latest Verified State

- Application protocol + `DEFAULT_KLINES_PAGE_LIMIT` owned in `application/market_data`
- Infrastructure `BinanceFuturesPublicClient` has no duplicate protocol and always uses `PRODUCTION_ORIGIN`
- Candle UTC policy: naive and non-zero-offset timestamps rejected; `close_time >= open_time`
- Finite-decimal policy: `parse_decimal` + `Candle` reject NaN / ±Infinity
- Fixture and mocked import hashes unchanged from Milestone 0.4

Fixture manifest hash:
`5a0f0d0aacc3bc06969c4d45a38906a8d8a423ab449178b22fbf6a8abe81df80`

Mocked 1005-candle import:
- normalized_sha256: `e54d56e814276e63574c57a66c6776bf3add0827c8401f354362695a34933159`
- content_hash: `ac9762134a0eb1f24b3dd9012df72f01ad19d4c1aa628188fcd6265195c3fc6e`

## 6–8. Product / Architecture / Research Engine

Corrective only. No candle-query API, resampling, indicators, strategies, backtesting, campaigns, candidates, scoring, worker leasing, autonomous research, MOMO, or trading.

## 9. Outstanding Work

Awaiting independent review of Milestone 0.4A.
No later milestone is authorized.

## 10. Verification Evidence (Milestone 0.4A)

Commands actually executed:

```text
uv sync --frozen --all-extras   # via uv run / prior lock
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest tests/unit -q                                          # 160 passed
uv run pytest tests/integration/test_artifact_filesystem.py -q       # 9 passed
uv run pytest tests/integration -q -m integration                    # 29 passed
alembic upgrade/downgrade round-trip through 0002 and base           # OK
uv run zorqen-dataset publish-fixture                                # created=true, same fixture hash
uv run zorqen-dataset publish-fixture                                # created=false, same hash
uv run python -m zorqen_research.worker --check                      # OK
frontend npm ci / lint / test / build                                # 15 tests
docker compose --profile fixture --profile binance-import build ...
docker compose up -d postgres migrate api worker frontend
docker compose --profile fixture run --rm --no-deps -T dataset-fixture
docker compose --profile binance-import run --rm -T binance-import --help
curl.exe nginx health/live, health/ready, strategy-families, datasets
docker compose logs ...; docker compose down -v
```

Live Binance smoke: not rerun (client still targets the same fixed production origin; transport injection tests cover the constructor change).

GitHub Actions: unknown until push.

## 11. Known Defects and Limitations

Unchanged from Milestone 0.4 (no candle-row query, no Parquet, no websockets).

## 12. Next Authorized Work

None until Milestone 0.4A is independently accepted.
