# Zorqen Research - Project Status

> This file records verified repository reality for handoff between coding agents. It must be updated in every milestone commit. Git, tests, and implementation remain authoritative when this file is stale or incorrect.

## 1. Project Identity

- Product: Zorqen Research
- Repository: `ZavierAhmed/Zorqen-Research`
- Default branch: `main`
- Current branch: `main`
- Previous verified commit (Milestone 1.2A): `23eac14ee54e6809865bd14c464333bd7fe39da2`
- Milestone 1.3 base commit: `23eac14ee54e6809865bd14c464333bd7fe39da2`
- Milestone result commit: current HEAD containing this status update (exact SHA after commit).
- Pinned MOMO Quant authority: `766e31db73bbb130d12ba84f1568745210db6155`
- Master specification: `docs/specification/Zorqen_Research_Master_Specification_v0.1.pdf`
- Current environment: Windows development laptop
- Target deployment: Windows or Linux VPS
- Runtime principle: CPU-first; no mandatory GPU dependency
- Push / GitHub state: report from final `git status -sb` and Actions after push; milestone incomplete until all four checks are green. Do not push unless instructed.

## 2. Product Purpose

Unchanged. Research qualification only; no account/trading APIs.

## 3. Initial Strategy Scope

Family metadata remains seeded. Milestone 1.3 freezes Adaptive MTF baseline authority as `RESOLVED`. No Adaptive MTF / S&R strategy provider is implemented.

## 4. Current Milestone

- Milestone: `1.3` — Resolve the Authoritative Adaptive MTF Baseline Contract
- Status: Complete pending independent review and all four GitHub checks green after push
- Base: `23eac14ee54e6809865bd14c464333bd7fe39da2`
- Work completed:
  - Baseline package under `domain/baselines` + `application/baselines`
  - `baselines/adaptive_mtf_trend_breakout/v1/` contract, evidence, approved definition
  - Parity fixtures from ported `AdaptiveDefaultFixtures`
  - `zorqen-strategy verify-baseline`
  - ADR 0013 + verification/traceability docs
- Implementation started: Yes
- Repository commit created: Yes (this milestone commit)
- Resolution status: **RESOLVED**
- `provider_implementation_allowed`: true (definition/contract only; no provider registered)

## 5. Latest Verified State

### Adaptive MTF baseline hashes (Milestone 1.3)

```text
baseline_contract_hash:    d7ac73fba9432e8a5e30392151d2f64864899f23c2b27a99db88857b3be2f89a
source_evidence_hash:      dc8417b0b68093860d6f17f650d08f7b56e277eab33a86a473b0931d33a0e9fb
strategy_definition_hash:  604ff40cb81e19f027b1422d3350d72b4dd02f8a48b9e50fc3f3c3a6666f93b1
fixture_manifest_hash:     71d311a0f3e5a2c5d70760b5458d4ab802f90148507257c6683611ed4b3bdd7d
definition_id:             b8e4f1a0-2c3d-4e5f-9687-1a2b3c4d5e6f
```

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

Baseline resolution freezes Adaptive MTF authority without registering a provider. Composition provenance from 1.2A unchanged. Indicator calculations, alignment, readiness, provider-visible hashes, strategy logic, persistence, API, frontend unchanged.

## 9. Outstanding Work

Awaiting independent review of Milestone 1.3. Milestone 1.4 (provider + parity) remains unauthorized.

## 10. Verification Evidence (Milestone 1.3)

Commands actually executed:

```text
uv sync --frozen --all-extras
uv run ruff check . / format --check / mypy src                  # pass (170 files)
uv run pytest tests/unit -k "baseline or adaptive_mtf or strategy_definition or parity_fixture" -q
                                                                 # 146 passed, 573 deselected
uv run pytest tests/unit -q                                      # 719 passed
uv run pytest tests/integration/test_artifact_filesystem.py -q   # 9 passed
uv run pytest tests/integration -q -m integration                # 34 passed
uv run pytest tests/integration/test_candle_query.py -q          # 5 passed
uv run zorqen-strategy verify-baseline --family adaptive_mtf_trend_breakout
                                                                 # twice; byte-identical; RESOLVED
alembic downgrade base / upgrade head                            # twice; head=0003
zorqen-indicators verify-golden / verify-view-golden             # pass; hashes preserved
zorqen-backtest / timeframes / mtf / mtf-indicator goldens       # pass; MTFIND hashes frozen
worker --check                                                   # PostgreSQL reachable
frontend npm ci / lint / test --run / build                      # 15 tests
docker compose ps + curl :5173 health/live/ready/families        # stack up; 200/200/200
Linux Quality (node:22-bookworm, UV_PROJECT_ENVIRONMENT=/tmp)    # LINUX_QUALITY_OK; 719 unit + verify-baseline
```

Traceability: `docs/verification/0013-adaptive-mtf-baseline-traceability.md` — **NOT TESTED: 0**

## 11. Known Defects / Limitations

- No Adaptive MTF / Support-Resistance strategy provider (signals, ATR stops, breakouts in Zorqen runtime).
- Support/Resistance baseline not resolved in this milestone.
- No indicator/backtest persistence, campaigns, API routes, or UI for baselines.

## 12. Next Authorized Work

Milestone 1.4 remains unauthorized pending independent review of Milestone 1.3.
