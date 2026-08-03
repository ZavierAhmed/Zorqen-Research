# Zorqen Research - Project Status

> This file records verified repository reality for handoff between coding agents. It must be updated in every milestone commit. Git, tests, and implementation remain authoritative when this file is stale or incorrect.

## 1. Project Identity

- Product: Zorqen Research
- Repository: `ZavierAhmed/Zorqen-Research`
- Default branch: `main`
- Current branch: `main`
- Previous verified commit (Milestone 0.5A): `f23c6749b4aeaf167d0dc2f1ff1a8530f8d706e9`
- Milestone 0.6 base commit: `f23c6749b4aeaf167d0dc2f1ff1a8530f8d706e9`
- Milestone result commit: current HEAD containing this status update.
- Exact SHA: report after commit.
- Master specification: `docs/specification/Zorqen_Research_Master_Specification_v0.1.pdf`
- Current environment: Windows development laptop
- Target deployment: Windows or Linux VPS
- Runtime principle: CPU-first; no mandatory GPU dependency
- Push state: confirm with `git status -sb` after commit (do not push unless instructed)

## 2. Product Purpose

Unchanged. Public market-data import, verified candle reads, and pure in-memory backtest kernel only; no account/trading APIs.

## 3. Initial Strategy Scope

Unchanged. Registry metadata only; executable strategy baselines not defined. Milestone 0.6 uses scripted golden providers only.

## 4. Current Milestone

- Milestone: `0.6` — Deterministic Bar-Based Backtest Kernel
- Status: Complete pending independent review
- Base: `f23c6749b4aeaf167d0dc2f1ff1a8530f8d706e9`
- Work completed:
  - Immutable backtest domain models and policy
  - `BacktestDecisionProvider` + `ScriptedDecisionProvider`
  - Deterministic single-position engine (market-on-next-open, long/short, stop/target, stop-first)
  - Decimal fees/slippage/P&L, fill/trade ledgers, realized-equity drawdown
  - Canonical result serialization/hashing
  - Seven golden scenarios + `zorqen-backtest` CLI
  - ADR 0006 and README kernel documentation
- Implementation started: Yes
- Repository commit created: Yes (this milestone commit)

## 5. Latest Verified State

- Candle querying and dataset hashes unchanged from Milestone 0.5A
- Golden CLI `run-golden --scenario all` exits 0 with stable hashes

Fixture manifest hash:
`5a0f0d0aacc3bc06969c4d45a38906a8d8a423ab449178b22fbf6a8abe81df80`

Mocked 1005-candle import:
- normalized_sha256: `e54d56e814276e63574c57a66c6776bf3add0827c8401f354362695a34933159`
- content_hash: `ac9762134a0eb1f24b3dd9012df72f01ad19d4c1aa628188fcd6265195c3fc6e`

Golden result hashes (Windows verification run):

```text
end-of-data:           28931b0cc74a136963be0d503742e7c04fc3e5df744f9d007350560f93f430c3
explicit-exit:         3d1134fb7ce251828cd8b4dd8840eac1b8a39c373df425d79d6692d40b840a1c
long-stop:             4b6b354b6f67af1aa06756b68513a2cc5a81066ba03a9c2d19bd939b733f1e02
long-target:           964dac42d637c0802a847ca5b63dec08c033d6234cbde71fff2b88c886a68a38
pending-final-entry:   e8721eab0f82f7ec9d43c0568c7f929deea2be6b4cd9ec1e84ebef1d5056a766
same-bar-stop-first:   a9273a5972f6bbae9dc9443385a2d3076dfc2a7549699e4a803e5899e2f928a6
short-target:          b342b5be8e4943a1bf82abbe26e3329424447515062df4e728154e47dea71c7d
```

## 6–8. Product / Architecture / Research Engine

Pure kernel only. No strategies, indicators, limit orders, funding/leverage, backtest API/persistence/UI, campaigns, candidates, scoring, MOMO, or trading.

## 9. Outstanding Work

Awaiting independent review of Milestone 0.6.
No later milestone is authorized.

## 10. Verification Evidence (Milestone 0.6)

Commands actually executed:

```text
uv sync --frozen --all-extras
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest tests/unit -q                                          # 242 passed
uv run pytest tests/integration/test_artifact_filesystem.py -q       # 9 passed
uv run pytest tests/integration -q -m integration                    # 34 passed
alembic upgrade/downgrade round-trip through 0002 and base           # OK
fixture + mocked import hash regression                              # unchanged
uv run zorqen-backtest run-golden --scenario all                     # twice, identical
uv run python -m zorqen_research.worker --check                      # OK
frontend npm ci / lint / test / build                                # 15 tests
docker compose smoke (fixture + nginx routes)                        # OK
```

GitHub Actions: unknown until push.

## 11. Known Defects and Limitations

- Mark-to-market drawdown deferred; only realized-equity drawdown is reported
- No limit/maker/partial fills, funding, leverage, or multi-position simulation
- No backtest HTTP API, persistence, or UI
- Full candle-partition read still required before candle query pages
- Windows artifact containment normalizes ``\\?\`` extended path prefixes so `relative_to` checks remain reliable

## 12. Next Authorized Work

None until Milestone 0.6 is independently accepted.
