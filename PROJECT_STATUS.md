# Zorqen Research - Project Status

> This file records verified repository reality for handoff between coding agents. It must be updated in every milestone commit. Git, tests, and implementation remain authoritative when this file is stale or incorrect.

## 1. Project Identity

- Product: Zorqen Research
- Repository: `ZavierAhmed/Zorqen-Research`
- Default branch: `main`
- Current branch: `main`
- Previous verified commit (Milestone 1.2): `aa310ea91a6751776eddf18529d100332fcd4276`
- Milestone 1.2A base commit: `aa310ea91a6751776eddf18529d100332fcd4276`
- Milestone result commit: current HEAD containing this status update (exact SHA after commit).
- Master specification: `docs/specification/Zorqen_Research_Master_Specification_v0.1.pdf`
- Current environment: Windows development laptop
- Target deployment: Windows or Linux VPS
- Runtime principle: CPU-first; no mandatory GPU dependency
- Push / GitHub state: report from final `git status -sb` and Actions after push; milestone incomplete until all four checks are green. Do not push unless instructed.

## 2. Product Purpose

Unchanged. Research qualification only; no account/trading APIs.

## 3. Initial Strategy Scope

Family metadata remains seeded. Milestone 1.2A seals composition provenance only — no Adaptive MTF / S&R signal algorithms.

## 4. Current Milestone

- Milestone: `1.2A` — Seal MTF indicator composition provenance
- Status: Complete pending independent review and all four GitHub checks green after push
- Base: `aa310ea91a6751776eddf18529d100332fcd4276`
- Work completed:
  - `reverify_indicator_composition` + complete composition identity comparison
  - Feed rebuilds and retains only trusted composition
  - Runner uses `feed.composition` only after feed creation
  - Envelope independently reverifies before hashing
  - Fully populated `object.__new__` forgery attacks + byte-identical replacement + controlled incomplete-object errors
  - Traceability 0012 updated (0 NOT TESTED)
- Implementation started: Yes
- Repository commit created: Yes (this milestone commit)

## 5. Latest Verified State

Preserved Milestone 1.2 composition / envelope hashes (unchanged):

```text
execution-indicator-warmup composition: 09c42366069a9be625274a0829314b986a714a66417a088794335cfb06015e01
execution-indicator-warmup envelope:    9b197291e0da4dbe3a16c8266f8868272217911a883ca6b7d39f0515412ebaae
exact-close-context composition:        65d5ebe74797553994e29ac7538bd745fefd6f2e9959949e2f92322cf9e5e93c
exact-close-context envelope:           b4fcff2a65ac6906d99b44adc45a3a8639d173af044d026bd516a20604e89370
```

Preserved Milestone 1.1 / MTF hashes (unchanged):

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

Composition provenance: every feed/runner/envelope path rebuilds via `from_verified` and compares canonical identity before use. No caller composition object retention. Unchanged indicator calculations, alignment, readiness, provider-visible hashes, strategy logic, persistence, API, frontend.

## 9. Outstanding Work

Awaiting independent review of Milestone 1.2A. Milestone 1.3 remains unauthorized.

## 10. Verification Evidence (Milestone 1.2A)

Commands actually executed:

```text
uv sync --frozen --all-extras
uv run ruff check . / format --check / mypy src                  # pass (162 files)
uv run pytest tests/unit -k "mtf_indicator or indicator_composition or composition_provenance" -q
                                                                 # 39 passed, 645 deselected
uv run pytest tests/unit -q                                      # 684 passed (Win + Linux)
uv run pytest tests/integration/test_artifact_filesystem.py -q   # 9 passed
uv run pytest tests/integration -q -m integration                # 34 passed
uv run pytest tests/integration/test_candle_query.py -q          # 5 passed
alembic downgrade base / upgrade head                            # twice; head=0003
zorqen-indicators verify-golden / verify-view-golden             # twice each; hashes preserved
zorqen-backtest / timeframes / mtf / mtf-indicator goldens       # twice each; MTFIND hashes frozen
worker --check                                                   # PostgreSQL reachable
frontend npm ci / lint / test --run / build                      # 15 tests
docker/nginx live/ready/families via :5173                       # ready/healthy/2/200
Linux Quality (node:22-bookworm, UV_PROJECT_ENVIRONMENT=/tmp)    # LINUX_QUALITY_OK
```

Traceability: `docs/verification/0012-multi-timeframe-indicator-composition-traceability.md` — **NOT TESTED: 0**

## 11. Known Defects / Limitations

- No Adaptive MTF / Support-Resistance strategy logic (signals, ATR stops, breakouts).
- No indicator/backtest persistence, campaigns, API routes, or UI for composition.

## 12. Next Authorized Work

Milestone 1.3 remains unauthorized pending independent review of Milestone 1.2A.
