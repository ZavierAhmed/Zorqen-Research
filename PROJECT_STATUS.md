# Zorqen Research - Project Status

> This file records verified repository reality for handoff between coding agents. It must be updated in every milestone commit. Git, tests, and implementation remain authoritative when this file is stale or incorrect.

## 1. Project Identity

- Product: Zorqen Research
- Repository: `ZavierAhmed/Zorqen-Research`
- Default branch: `main`
- Current branch: `main`
- Previous verified commit (Milestone 0.9C): `9b5f030c1209f435b481f60ed8571128f11a50be`
- Milestone 1.0 base commit: `9b5f030c1209f435b481f60ed8571128f11a50be`
- Milestone result commit: current HEAD containing this status update (exact SHA after commit).
- Master specification: `docs/specification/Zorqen_Research_Master_Specification_v0.1.pdf`
- Current environment: Windows development laptop
- Target deployment: Windows or Linux VPS
- Runtime principle: CPU-first; no mandatory GPU dependency
- Push / GitHub state: report from final `git status -sb` and Actions after push; milestone incomplete until all four checks are green. Do not push unless instructed.

## 2. Product Purpose

Unchanged. Research qualification only; no account/trading APIs.

## 3. Initial Strategy Scope

Family metadata remains seeded. Milestone 1.0 adds pure offline indicator series only — no executable Adaptive MTF / Support-Resistance algorithms or provider-safe indicator views.

## 4. Current Milestone

- Milestone: `1.0` — Deterministic Indicator Series Foundation
- Status: Complete pending independent review and all four GitHub checks green after push
- Base: `9b5f030c1209f435b481f60ed8571128f11a50be`
- Work completed:
  - Factory-bound `IndicatorInput` / `IndicatorSeries` with computed hashes
  - Fixed local Decimal math policy (`schema_version=1`, precision 50, `ROUND_HALF_EVEN`)
  - Indicators: `ema_close`, `true_range`, `wilder_atr`, inclusive and prior rolling extrema
  - Canonical JSON serialization + SHA-256 result hashing
  - Literal goldens + `zorqen-indicators verify-golden`
  - ADR 0010 + traceability 0010 (0 NOT TESTED) + red-team loop
  - No decision-feed / provider / persistence / API / migration integration
- Implementation started: Yes
- Repository commit created: Yes (this milestone commit)

## 5. Latest Verified State

Fixture / dataset / strategy-definition / resampling / alignment / MTF hashes: unchanged from Milestone 0.9C.

```text
exact-close bundle:   1ef63eff5e42d00d2d3edabbc849a3f1f651929c3ba52abbc08fd64497794167
exact-close envelope: 8e5259d68e152ee3c1b0767ec372866ddcbb8b67eeae96175345e2512879b70d
two-contexts envelope:c0945d5d2609c958a2cdae155e65606e59233a6fc6c03ec6906bc8065bfa0d94
```

Indicator golden result hashes (literal):

```text
ema_close:            982dcb739655d2eb018e74911c8d53a66a9f86555ffa74aa8111c7134482d303
true_range:           4fba21ba2715717330ccf16df77a89ecf2627e7413bfdf833f3136fecb31f938
wilder_atr:           0c4b742242ed3ca00527f8ebc1c990d36c7970347692fd235380ffdbb448667e
rolling_highest:      229d1a35dd067ac1d5e7fd6fe1fd6ee40ca6d91795fa7f4ab7c51f018b9384fa
rolling_lowest:       671ec35b969e7ecc36c44505d70205fc7fca4cdda047146790885c169ecdcf09
prior_rolling_highest:541d93b026b5f72eb44f62c8910294e088231f72a93bb9e4130209c0fe4a92c2
prior_rolling_lowest: 5e03c3acc6108612a30467b86b7ed6f17450794438f0d11849c881d1024fbfcc
```

## 6–8. Product / Architecture / Research Engine

Pure indicator kernel only. No strategy signals, provider factories, provider-safe indicator views, persistence/API/UI, campaigns, scoring, MOMO, or trading. Milestone 1.1 is not started.

## 9. Outstanding Work

Awaiting independent review of Milestone 1.0 and confirmation that all four GitHub checks are green after push.

## 10. Verification Evidence (Milestone 1.0)

Commands actually executed:

```text
uv sync --frozen --all-extras
uv run ruff check .                                            # All checks passed
uv run ruff format --check .                                   # 239 files already formatted
uv run mypy src                                                # Success: 143 source files
uv run pytest tests/unit -k "indicator or ema or true_range or atr or extrema" -q
                                                               # 143 passed, 422 deselected
uv run pytest tests/unit -q                                    # 565 passed (Win + Linux)
uv run pytest tests/integration/test_artifact_filesystem.py -q # 9 passed
uv run pytest tests/integration -q -m integration              # 34 passed (with Postgres)
uv run pytest tests/integration/test_candle_query.py -q        # 5 passed
alembic downgrade base / upgrade head (×2)                     # 0001/0002/0003 only
uv run zorqen-indicators verify-golden --scenario all          # twice, byte-identical
uv run zorqen-backtest run-golden --scenario all               # twice, hashes preserved
uv run zorqen-timeframes verify-golden --scenario all          # twice, hashes preserved
uv run zorqen-backtest run-mtf-golden --scenario all           # twice, MTF hashes preserved
uv run python -m zorqen_research.worker --check                # PostgreSQL reachable
frontend npm ci / lint / test --run / build                    # 15 passed; build ok
docker compose nginx live/ready/families                       # 200/200/200
Linux (uv python3.12-bookworm-slim): ruff/mypy; 565 unit; all golden CLIs
Linux (node:22-bookworm): quality.yml sequence + goldens + frontend 15 + build
```

Traceability: `docs/verification/0010-indicator-foundation-traceability.md` — **NOT TESTED: 0**

GitHub Actions: unknown until push.

## 11. Known Defects and Limitations

- No concrete Adaptive MTF / Support-Resistance provider
- No provider-safe bounded indicator views (deferred)
- No indicator persistence / API / UI
- No backtest/strategy persistence or API
- MTF runner rejects definitions without context requirements (use single-TF path)

## 12. Next Authorized Work

None until Milestone 1.0 is independently accepted. Milestone 1.1 is not authorized.
