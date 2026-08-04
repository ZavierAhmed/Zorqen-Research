# ADR 0010 — Deterministic Indicator Series Foundation

## Status

Accepted (Milestone 1.0)

## Context

Future Adaptive Multi-Timeframe Trend Breakout and Support/Resistance providers need stable offline indicator series (EMA, True Range, Wilder ATR, rolling extrema). Those series must be deterministic across Windows and Linux, free of third-party TA libraries, and independent of FastAPI, SQLAlchemy, strategy providers, and decision feeds.

Complete offline `IndicatorSeries` objects may contain values for bars that would be “future” relative to an individual backtest decision. Provider-safe bounded indicator views therefore remain deferred.

## Decision

1. **Pure indicator kernel.** Domain models (`IndicatorInput`, `IndicatorSeries`, math policy, codes) and application calculators live outside API, persistence, and strategy-provider packages. No NumPy, pandas, or TA-Lib.
2. **Fixed local Decimal policy.** Schema `"1"`, precision `50`, `ROUND_HALF_EVEN`. Every division and recurrence runs under `decimal.localcontext`. Callers cannot supply alternate precision. Process-global Decimal context mutations must not alter outputs.
3. **Factory-bound input and calculator-owned results.** `IndicatorInput.from_verified` requires exact `tuple` / `Candle` runtime types and computes metadata and SHA-256 hashes. `IndicatorSeries` is assembled only by calculator-owned `_calculated_indicator_series`, which enforces code-specific parameters, warmup shape, and non-negativity. Direct construction and public value injection are rejected. Candle identity reuses the canonical CSV serializer.
4. **Warmup as `None`.** Undefined warmup slots are JSON `null` / Python `None`, never NaN.
5. **EMA.** Seed with SMA of the first `P` closes at index `P-1`; then `ema += α*(close-ema)` with `α=2/(P+1)`. Period `1` equals close.
6. **True Range / Wilder ATR.** First TR is high−low; later TR is the max of high−low and absolute gaps to prior close. ATR seeds on the mean of the first `P` TR values, then Wilder recurrence `(ATR*(P-1)+TR)/P`.
7. **Inclusive vs prior extrema.** Inclusive rolling windows include the current candle. Prior-window extrema use only `i-P..i-1` so breakout checks cannot contaminate with the current bar. Both use monotonic deques for O(n) time.
8. **No provider integration.** Do not attach `IndicatorSeries` to `BacktestDecisionContext`, `MultiTimeframeBacktestDecisionContext`, `VisibleCandleHistory`, or decision feeds. Provider-safe bounded views, persistence, and caching are deferred.
9. **Verification.** Literal golden vectors + `zorqen-indicators verify-golden` freeze values and hashes without loading files or contacting a database.

## Consequences

- Strategy providers in later milestones must consume visibility-bounded indicator views, not complete offline series.
- A future governed math-policy schema version may introduce another Decimal policy; precision remains non-strategy-parameter.
- Adding indicators requires new explicit `IndicatorCode` values, calculators, goldens, and tests — not a plugin expression framework.
