# ADR 0008 — Deterministic Timeframe Resampling and Alignment

## Status

Accepted (Milestone 0.8 / 0.8A)

## Context

Strategies such as Adaptive MTF Trend Breakout need higher-timeframe context built from verified lower-timeframe candles. Resampling must be exact, reproducible, and free of lookahead before any provider or backtest integration.

## Decision

1. **Exact integer ratios only.** A target timeframe is accepted only when its duration is a strict integer multiple of the source duration (computed in whole milliseconds). Non-integral pairs such as `3m → 5m` fail. This avoids ambiguous bucket membership and floating-point ratio math.
2. **Complete buckets only.** Leading or trailing partial buckets fail. Every target bucket must contain exactly `ratio` contiguous source children whose opens equal `target_open + i × source_duration`. Partial buckets are never dropped or synthesized.
3. **UTC canonical boundaries.** Source opens must align to the source timeframe; the first open must also align to the target timeframe via the existing floor rules. Weekly buckets begin Monday `00:00:00 UTC`.
4. **Exact OHLCV aggregation.** Open/high/low/close use first/max/min/last child values; volume fields and trade counts sum exactly with `Decimal` / `int`. No rounding and no binary floats.
5. **Context availability by close time.** A context candle is visible to an execution decision iff `context.close_time <= execution.close_time`. Equality at the decision close is allowed; a context closing one millisecond later is not.
6. **Monotonic pointer alignment.** Alignment advances a single context index across the execution series in linear time and never returns future context indexes or bodies.
7. **Computed hashes.** Source/target candle SHA-256 digests use existing canonical CSV bytes. Alignment hashes bind symbol, timeframes, series hashes, and index mappings — not candle bodies twice. Milestone 0.8A makes result models factory-only: counts, bounds, and hashes are computed from verified candle tuples; public APIs reject caller-supplied hashes and arbitrary mappings. Single-context results carry their own `alignment_hash`; multi-context hashes also bind ordered child alignment hashes.
8. **Deferred integration.** No changes to `BacktestDecisionContext`, provider factories, persistence, APIs, or strategy logic in this milestone.

## Consequences

- Higher-timeframe series used by future strategies must be produced through this pure path.
- Incomplete coverage cannot silently become a shorter series.
- Golden CLI `zorqen-timeframes verify-golden` freezes resampling and alignment vectors.
