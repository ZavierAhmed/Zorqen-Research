# Zorqen Research - Project Status

> This file records verified repository reality for handoff between coding agents. It must be updated in every milestone commit. Git, tests, and implementation remain authoritative when this file is stale or incorrect.

## 1. Project Identity

- Product: Zorqen Research
- Repository: `ZavierAhmed/Zorqen-Research`
- Default branch: `main`
- Current branch: `main`
- Previous verified commit (Milestone 0.9): `b8080301a5f70d8a3ed42203479a4927778eb826`
- Milestone 0.9A base commit: `b8080301a5f70d8a3ed42203479a4927778eb826`
- Milestone result commit: current HEAD containing this status update (exact SHA after commit).
- Master specification: `docs/specification/Zorqen_Research_Master_Specification_v0.1.pdf`
- Current environment: Windows development laptop
- Target deployment: Windows or Linux VPS
- Runtime principle: CPU-first; no mandatory GPU dependency
- Push / GitHub state: report from final `git status -sb` and Actions after push; milestone incomplete until all four checks are green. Do not push unless instructed.

## 2. Product Purpose

Unchanged. Research qualification only; no account/trading APIs.

## 3. Initial Strategy Scope

Family metadata remains seeded. Milestone 0.9A is a corrective identity/performance fix only — no executable Adaptive MTF / Support-Resistance algorithms.

## 4. Current Milestone

- Milestone: `0.9A` — Bind MTF run identity and optimize decision views
- Status: Complete pending independent review and all four GitHub checks green after push
- Base: `b8080301a5f70d8a3ed42203479a4927778eb826`
- Work completed:
  - `StrategyBacktestEnvelope.from_run` derives all logical hashes; no caller-hash factory
  - Adapter/view factories bind identities only from the feed/bundle
  - `VerifiedHistorySource` + O(1) per-bar `VisibleCandleHistory.from_verified_source`
  - Exact tuple contract (`type is tuple`); direction golden proves unsupported-direction cause with truthful invocation count
  - Traceability 0009 rows for 0.9A (0 NOT TESTED)
- Implementation started: Yes
- Repository commit created: Yes (this milestone commit)

## 5. Latest Verified State

Fixture / dataset / strategy-definition / resampling / alignment hashes: unchanged from Milestone 0.8A / 0.9.

Golden backtest hashes (unchanged):

```text
28931b0cc74a136963be0d503742e7c04fc3e5df744f9d007350560f93f430c3
3d1134fb7ce251828cd8b4dd8840eac1b8a39c373df425d79d6692d40b840a1c
4b6b354b6f67af1aa06756b68513a2cc5a81066ba03a9c2d19bd939b733f1e02
964dac42d637c0802a847ca5b63dec08c033d6234cbde71fff2b88c886a68a38
e8721eab0f82f7ec9d43c0568c7f929deea2be6b4cd9ec1e84ebef1d5056a766
a9273a5972f6bbae9dc9443385a2d3076dfc2a7549699e4a803e5899e2f928a6
b342b5be8e4943a1bf82abbe26e3329424447515062df4e728154e47dea71c7d
```

Selected MTF bridge golden hashes (unchanged):

```text
exact-close bundle:   1ef63eff5e42d00d2d3edabbc849a3f1f651929c3ba52abbc08fd64497794167
exact-close envelope: 8e5259d68e152ee3c1b0767ec372866ddcbb8b67eeae96175345e2512879b70d
two-contexts envelope:c0945d5d2609c958a2cdae155e65606e59233a6fc6c03ec6906bc8065bfa0d94
```

Direction-restriction CLI payload now reports:

```text
controlled_failure: true
provider_invocation_count: 1
first_ready_index: 3
error_code: unsupported_direction
```

## 6–8. Product / Architecture / Research Engine

No strategy algorithms, indicators, dynamic provider factories, persistence/API/UI, campaigns, scoring, MOMO, or trading. Milestone 1.0 is not started.

## 9. Outstanding Work

Awaiting independent review of Milestone 0.9A and confirmation that all four GitHub checks are green after push.

## 10. Verification Evidence (Milestone 0.9A)

Commands actually executed:

```text
uv sync --frozen --all-extras
uv run ruff check .                                            # All checks passed
uv run ruff format --check .                                   # 212 files already formatted
uv run mypy src                                                # Success: 129 source files
uv run pytest tests/unit -k "multi_timeframe or decision_feed or strategy_backtest or identity_binding_09a" -q
                                                               # 21 passed, 463 deselected
uv run pytest tests/unit -q                                    # 484 passed (Win + Linux)
uv run pytest tests/integration/test_artifact_filesystem.py -q # 9 passed
uv run pytest tests/integration -q -m integration              # 34 passed (with Postgres)
uv run pytest tests/integration/test_candle_query.py -q        # 5 passed
alembic downgrade base / upgrade head (×2)                     # 0001/0002/0003 only
uv run zorqen-backtest run-golden --scenario all               # twice, hashes preserved
uv run zorqen-timeframes verify-golden --scenario all          # twice, hashes preserved
uv run zorqen-backtest run-mtf-golden --scenario all           # twice, hashes preserved
uv run python -m zorqen_research.worker --check                # PostgreSQL reachable
frontend npm ci / lint / test --run / build                    # 15 passed; build ok
docker compose build + nginx live/ready/families/fixture       # 200; fixture hash preserved
Linux container (node:22-bookworm): quality.yml sequence       # ruff/mypy; 484 unit; frontend 15 + build
```

Traceability: `docs/verification/0009-multi-timeframe-backtest-traceability.md` — **NOT TESTED: 0**

GitHub Actions: unknown until push.

## 11. Known Defects and Limitations

- No concrete Adaptive MTF / Support-Resistance provider
- No backtest/strategy persistence or API
- MTF runner rejects definitions without context requirements (use single-TF path)

## 12. Next Authorized Work

None until Milestone 0.9A is independently accepted. Milestone 1.0 is not authorized.
