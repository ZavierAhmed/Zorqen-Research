# Zorqen Research - Project Status

> This file records verified repository reality for handoff between coding agents. It must be updated in every milestone commit. Git, tests, and implementation remain authoritative when this file is stale or incorrect.

## 1. Project Identity

- Product: Zorqen Research
- Repository: `ZavierAhmed/Zorqen-Research`
- Default branch: `main`
- Current branch: `main`
- Previous verified commit (Milestone 1.1): `a19c57368979e0e97db5dc885c09087809f14ced`
- Milestone 1.1A base commit: `a19c57368979e0e97db5dc885c09087809f14ced`
- Milestone result commit: current HEAD containing this status update (exact SHA after commit).
- Master specification: `docs/specification/Zorqen_Research_Master_Specification_v0.1.pdf`
- Current environment: Windows development laptop
- Target deployment: Windows or Linux VPS
- Runtime principle: CPU-first; no mandatory GPU dependency
- Push / GitHub state: report from final `git status -sb` and Actions after push; milestone incomplete until all four checks are green. Do not push unless instructed.

## 2. Product Purpose

Unchanged. Research qualification only; no account/trading APIs.

## 3. Initial Strategy Scope

Family metadata remains seeded. Milestone 1.1A seals indicator bundle provenance only — no MTF provider composition or strategy algorithms.

## 4. Current Milestone

- Milestone: `1.1A` — Seal indicator bundle provenance and feed identity
- Status: Complete pending independent review and all four GitHub checks green after push
- Base: `a19c57368979e0e97db5dc885c09087809f14ced`
- Work completed:
  - Exact `IndicatorInput` type + candle reconstruction before bundle accept
  - Closed `recalculate_indicator_series` dispatcher; retain calculator output only
  - Bundle document/hash helpers; feed rebuilds trusted bundle and compares identity
  - Provenance adversarial tests (forged input/series/bundle)
  - Traceability 0011 updated (0 NOT TESTED)
- Implementation started: Yes
- Repository commit created: Yes (this milestone commit)

## 5. Latest Verified State

All Milestone 1.1 view / indicator / MTF hashes preserved (unchanged).

```text
warmup bundle:         b9e4c70816cf3118632fbeb1274b52a1b70fedc1bb92b0f514ac442a59e94e7a
warmup final view:     aaecdb9c79d1d2649ed37087bcbc3a3652f1e4e7466b4a315efe1a104479a847
multiple-ema bundle:   6bf1290f021bd5ccf03ec1f8faecbbef8af9286642e83551d10d09751a8a45cf
multiple-ema view:     8607acdd9b9cf776a804df7e0fcf71bd6cb06140938d2f336f9fa906041c96e2
future prefix view:    b5df80fbb92a71f0b8b01c93cfb08baaf88abccbab39945e0103482a11a48928
exact-close bundle:    1ef63eff5e42d00d2d3edabbc849a3f1f651929c3ba52abbc08fd64497794167
exact-close envelope:  8e5259d68e152ee3c1b0767ec372866ddcbb8b67eeae96175345e2512879b70d
two-contexts envelope: c0945d5d2609c958a2cdae155e65606e59233a6fc6c03ec6906bc8065bfa0d94
```

## 6–8. Product / Architecture / Research Engine

Standalone bounded indicator feed with sealed provenance. No strategy signals, no MTF indicator composition, no persistence/API/UI. Milestone 1.2 is not started.

## 9. Outstanding Work

Awaiting independent review of Milestone 1.1A. Milestone 1.2 remains unauthorized.

## 10. Verification Evidence (Milestone 1.1A)

Commands actually executed:

```text
uv sync --frozen --all-extras
uv run ruff check . / format --check / mypy src                  # pass
uv run pytest tests/unit -k "indicator_view or indicator_feed or indicator_bundle or provenance" -q
                                                                 # 68 passed
uv run pytest tests/unit -q                                      # 645 passed (Win + Linux)
uv run pytest tests/integration/test_artifact_filesystem.py -q   # 9 passed
uv run pytest tests/integration -q -m integration                # 34 passed
uv run pytest tests/integration/test_candle_query.py -q          # 5 passed
alembic downgrade base / upgrade head                            # 0001–0003; head=0003
zorqen-indicators verify-golden / verify-view-golden             # twice each; hashes preserved
zorqen-backtest / timeframes / mtf goldens                       # twice each
worker --check                                                   # PostgreSQL reachable
frontend npm ci / lint / test --run / build                      # 15 tests
docker/nginx live/ready/families                                 # healthy/ready/200
Linux Quality (node:22-bookworm)                                 # pass
```

Traceability: `docs/verification/0011-bounded-indicator-feed-traceability.md` — **NOT TESTED: 0**

## 11. Known Defects / Limitations

- Indicator decision feed is standalone; not attached to MTF providers (deferred to 1.2).
- No Adaptive MTF / Support-Resistance strategy logic.

## 12. Next Authorized Work

Milestone 1.2 remains unauthorized pending independent review of Milestone 1.1A.
