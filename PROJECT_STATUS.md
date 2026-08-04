# Zorqen Research - Project Status

> This file records verified repository reality for handoff between coding agents. It must be updated in every milestone commit. Git, tests, and implementation remain authoritative when this file is stale or incorrect.

## 1. Project Identity

- Product: Zorqen Research
- Repository: `ZavierAhmed/Zorqen-Research`
- Default branch: `main`
- Current branch: `main`
- Previous verified commit (Milestone 0.9B): `c5dd8baaaefaf945b62ab08da56a41ff237e26c3`
- Milestone 0.9C base commit: `c5dd8baaaefaf945b62ab08da56a41ff237e26c3`
- Milestone result commit: current HEAD containing this status update (exact SHA after commit).
- Master specification: `docs/specification/Zorqen_Research_Master_Specification_v0.1.pdf`
- Current environment: Windows development laptop
- Target deployment: Windows or Linux VPS
- Runtime principle: CPU-first; no mandatory GPU dependency
- Push / GitHub state: report from final `git status -sb` and Actions after push; milestone incomplete until all four checks are green. Do not push unless instructed.

## 2. Product Purpose

Unchanged. Research qualification only; no account/trading APIs.

## 3. Initial Strategy Scope

Family metadata remains seeded. Milestone 0.9C seals history representation only — no executable Adaptive MTF / Support-Resistance algorithms.

## 4. Current Milestone

- Milestone: `0.9C` — Seal history representation boundaries
- Status: Complete pending independent review and all four GitHub checks green after push
- Base: `c5dd8baaaefaf945b62ab08da56a41ff237e26c3`
- Work completed:
  - `VisibleCandleHistory` / `_VerifiedHistorySource` use `repr=False` plus safe O(1) `__repr__`/`__str__`
  - Nested decision-view and enhanced provider-context representations do not leak future candles
  - NoLookaheadProbeProvider extended to probe repr/str paths
  - Traceability 0009 rows for 0.9C (0 NOT TESTED)
- Implementation started: Yes
- Repository commit created: Yes (this milestone commit)

## 5. Latest Verified State

Fixture / dataset / strategy-definition / resampling / alignment / MTF hashes: unchanged from Milestone 0.9B.

```text
exact-close bundle:   1ef63eff5e42d00d2d3edabbc849a3f1f651929c3ba52abbc08fd64497794167
exact-close envelope: 8e5259d68e152ee3c1b0767ec372866ddcbb8b67eeae96175345e2512879b70d
two-contexts envelope:c0945d5d2609c958a2cdae155e65606e59233a6fc6c03ec6906bc8065bfa0d94
```

## 6–8. Product / Architecture / Research Engine

No strategy algorithms, indicators, dynamic provider factories, persistence/API/UI, campaigns, scoring, MOMO, or trading. Milestone 1.0 is not started.

## 9. Outstanding Work

Awaiting independent review of Milestone 0.9C and confirmation that all four GitHub checks are green after push.

## 10. Verification Evidence (Milestone 0.9C)

Commands actually executed:

```text
uv sync --frozen --all-extras
uv run ruff check .                                            # All checks passed
uv run ruff format --check .                                   # 214 files already formatted
uv run mypy src                                                # Success: 129 source files
uv run pytest tests/unit -k "multi_timeframe or decision_feed or strategy_backtest or no_lookahead or history_repr" -q
                                                               # 29 passed, 463 deselected
uv run pytest tests/unit -q                                    # 492 passed (Win + Linux)
uv run pytest tests/integration/test_artifact_filesystem.py -q # 9 passed
uv run pytest tests/integration -q -m integration              # 34 passed (with Postgres)
uv run pytest tests/integration/test_candle_query.py -q        # 5 passed
alembic downgrade base / upgrade head (×2)                     # 0001/0002/0003 only
uv run zorqen-backtest run-golden --scenario all               # twice, hashes preserved
uv run zorqen-timeframes verify-golden --scenario all          # twice, hashes preserved
uv run zorqen-backtest run-mtf-golden --scenario all           # twice, hashes preserved
uv run python -m zorqen_research.worker --check                # PostgreSQL reachable
frontend npm ci / lint / test --run / build                    # 15 passed; build ok
docker compose nginx live/ready/families                       # ok
Linux container (node:22-bookworm): quality.yml sequence       # ruff/mypy; 492 unit; frontend 15 + build
```

Traceability: `docs/verification/0009-multi-timeframe-backtest-traceability.md` — **NOT TESTED: 0**

GitHub Actions: unknown until push.

## 11. Known Defects and Limitations

- No concrete Adaptive MTF / Support-Resistance provider
- No backtest/strategy persistence or API
- MTF runner rejects definitions without context requirements (use single-TF path)

## 12. Next Authorized Work

None until Milestone 0.9C is independently accepted. Milestone 1.0 is not authorized.
