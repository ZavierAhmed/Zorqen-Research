# ADR 0009 — Deterministic Multi-Timeframe Backtest Decision Feed

## Status

Accepted (Milestone 0.9)

## Context

Milestone 0.8/0.8A produced verified resampling and no-lookahead alignment. Milestone 0.7 produced immutable strategy definitions with execution/context warmups. The existing `BacktestEngine` already owns fills, stops, fees, and result hashing. Strategies need a bridge that feeds no-lookahead multi-timeframe views into that engine without rewriting fill math or implementing a concrete strategy.

## Decision

1. **Keep the engine unchanged.** `BacktestEngine` remains the only execution loop. The bridge supplies a `BacktestDecisionProvider` adapter and passes the execution candle hash as `expected_input_hash`.
2. **Adapter wraps the multi-timeframe provider.** The adapter receives the single-timeframe context, builds a decision view from the feed, skips the underlying provider until overall readiness, then calls it once with an enhanced context.
3. **Visibility-bounded histories.** `VisibleCandleHistory` exposes only `candles[0:end_exclusive]`. Ordinary indexing, slicing, and iteration cannot reach future candles.
4. **Exact-close context is available.** Alignment mapping uses `context.close_time <= execution.close_time`, matching ADR 0008.
5. **Warmup zero still requires one closed context candle.** Readiness uses `max(1, warmup_bars)` so a declared context is never “ready” with zero closed bars.
6. **Underlying provider is not called during warmup.** Warmup-skipped closes return `()` without invoking strategy code.
7. **Envelope is separate from `BacktestResult`.** `StrategyBacktestEnvelope` binds strategy instance, input bundle, execution/context identities, policy, and the unchanged result hash without mutating `BacktestResult`.
8. **Deferred strategy/provider factories.** No concrete Adaptive MTF / Support-Resistance algorithms, dynamic imports, or persistence in this milestone.

## Consequences

- Future strategy providers implement `MultiTimeframeDecisionProvider` only.
- Single-timeframe definitions continue on the existing path and are rejected by the MTF runner.
- Golden CLI `zorqen-backtest run-mtf-golden` freezes bridge identity independently of the seven single-timeframe result hashes.
