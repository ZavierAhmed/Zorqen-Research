# Zorqen Research - Project Status

> This file records verified repository reality for handoff between coding agents. It must be updated in every milestone commit. Git, tests, and implementation remain authoritative when this file is stale or incorrect.

## 1. Project Identity

- Product: Zorqen Research
- Repository: `ZavierAhmed/Zorqen-Research`
- Default branch: `main`
- Current branch: `main`
- Previous verified commit (Milestone 1.0A): `0554d51793c3bfe9021d475fa2b23a749ccbf76c`
- Milestone 1.1 base commit: `0554d51793c3bfe9021d475fa2b23a749ccbf76c`
- Milestone result commit: current HEAD containing this status update (exact SHA after commit).
- Master specification: `docs/specification/Zorqen_Research_Master_Specification_v0.1.pdf`
- Current environment: Windows development laptop
- Target deployment: Windows or Linux VPS
- Runtime principle: CPU-first; no mandatory GPU dependency
- Push / GitHub state: report from final `git status -sb` and Actions after push; milestone incomplete until all four checks are green. Do not push unless instructed.

## 2. Product Purpose

Unchanged. Research qualification only; no account/trading APIs.

## 3. Initial Strategy Scope

Family metadata remains seeded. Milestone 1.1 adds standalone bounded indicator views only — no executable Adaptive MTF / Support-Resistance algorithms and no MTF provider composition.

## 4. Current Milestone

- Milestone: `1.1` — Add no-lookahead bounded indicator decision feed
- Status: Complete pending independent review and all four GitHub checks green after push
- Base: `0554d51793c3bfe9021d475fa2b23a749ccbf76c`
- Work completed:
  - `IndicatorSeriesKey`, `IndicatorSeriesBundle`, `_VerifiedIndicatorSource`, `VisibleIndicatorHistory`
  - Prefix-only hash chains + `IndicatorDecisionFeed` / `IndicatorDecisionView` / `IndicatorDecisionItem`
  - Literal view goldens + `zorqen-indicators verify-view-golden`
  - ADR 0011 + traceability 0011 (0 NOT TESTED)
  - Existing MTF/provider types untouched; no strategy signals; no persistence/API/UI
- Implementation started: Yes
- Repository commit created: Yes (this milestone commit)

## 5. Latest Verified State

Fixture / dataset / strategy-definition / resampling / alignment / MTF hashes: unchanged from Milestone 1.0A.

```text
exact-close bundle:   1ef63eff5e42d00d2d3edabbc849a3f1f651929c3ba52abbc08fd64497794167
exact-close envelope: 8e5259d68e152ee3c1b0767ec372866ddcbb8b67eeae96175345e2512879b70d
two-contexts envelope:c0945d5d2609c958a2cdae155e65606e59233a6fc6c03ec6906bc8065bfa0d94
```

Indicator series golden result hashes (unchanged):

```text
ema_close:             982dcb739655d2eb018e74911c8d53a66a9f86555ffa74aa8111c7134482d303
ema_recursive:         c59617e531bf61918fbfe349774618df18259f76723275f3d543ac3241779f96
true_range:            4fba21ba2715717330ccf16df77a89ecf2627e7413bfdf833f3136fecb31f938
wilder_atr:            0c4b742242ed3ca00527f8ebc1c990d36c7970347692fd235380ffdbb448667e
rolling_highest:       229d1a35dd067ac1d5e7fd6fe1fd6ee40ca6d91795fa7f4ab7c51f018b9384fa
rolling_lowest:        671ec35b969e7ecc36c44505d70205fc7fca4cdda047146790885c169ecdcf09
prior_rolling_highest: 541d93b026b5f72eb44f62c8910294e088231f72a93bb9e4130209c0fe4a92c2
prior_rolling_lowest:  5e03c3acc6108612a30467b86b7ed6f17450794438f0d11849c881d1024fbfcc
```

New view golden hashes (Milestone 1.1):

```text
warmup bundle:         b9e4c70816cf3118632fbeb1274b52a1b70fedc1bb92b0f514ac442a59e94e7a
warmup final view:     aaecdb9c79d1d2649ed37087bcbc3a3652f1e4e7466b4a315efe1a104479a847
multiple-ema bundle:   6bf1290f021bd5ccf03ec1f8faecbbef8af9286642e83551d10d09751a8a45cf
multiple-ema view:     8607acdd9b9cf776a804df7e0fcf71bd6cb06140938d2f336f9fa906041c96e2
future-A bundle:       608b2dc2a90a097e8a18b3521cf88f1198c0058b0cc08119ed95e7c5b629edea
future-B bundle:       858c3d7e2cb2a279165c11a09c9184ef40fb99bdd080a2dc7f42dc975a264dae
future prefix view:    b5df80fbb92a71f0b8b01c93cfb08baaf88abccbab39945e0103482a11a48928
```

## 6–8. Product / Architecture / Research Engine

Standalone bounded indicator feed only. No strategy signals, no MTF indicator composition, no provider factories, no persistence/API/UI, campaigns, scoring, MOMO, or trading. Milestone 1.2 is not started.

## 9. Outstanding Work

Awaiting independent review of Milestone 1.1 and confirmation that all four GitHub checks are green after push. Milestone 1.2 remains unauthorized.

## 10. Verification Evidence (Milestone 1.1)

Commands actually executed:

```text
uv sync --frozen --all-extras
uv run ruff check .                                              # pass
uv run ruff format --check .                                     # pass
uv run mypy src                                                  # Success: 154 source files
uv run pytest tests/unit -k "indicator_view or indicator_feed or visible_indicator or prefix_hash" -q
                                                                 # 47 passed
uv run pytest tests/unit -q                                      # 629 passed
uv run pytest tests/integration/test_artifact_filesystem.py -q   # 9 passed
uv run pytest tests/integration -q -m integration                # 34 passed
uv run pytest tests/integration/test_candle_query.py -q          # 5 passed
alembic downgrade base / upgrade head (×2)                       # 0001/0002/0003 only; head=0003
uv run zorqen-indicators verify-golden --scenario all            # twice, all ok (hashes unchanged)
uv run zorqen-indicators verify-view-golden --scenario all       # twice, all ok
uv run zorqen-backtest run-golden --scenario all                 # twice
uv run zorqen-timeframes verify-golden --scenario all            # twice
uv run zorqen-backtest run-mtf-golden --scenario all             # twice (exact-close bundle/envelope unchanged)
uv run python -m zorqen_research.worker --check                  # PostgreSQL reachable
frontend npm ci / lint / test --run / build                      # 15 tests; production build ok
docker/nginx: /api/v1/health/live, ready, strategy-families      # 200 / ready / 200
Linux Quality (node:22-bookworm): ruff/mypy/unit(629)/frontend   # pass
```

Traceability: `docs/verification/0011-bounded-indicator-feed-traceability.md` — **NOT TESTED: 0**

## 11. Known Defects / Limitations

- Indicator decision feed is standalone; not attached to MTF providers (deferred to 1.2).
- No indicator persistence, caching, HTTP routes, or UI.
- No Adaptive MTF / Support-Resistance strategy logic.

## 12. Next Authorized Work

Milestone 1.2 remains unauthorized pending independent review of Milestone 1.1.
