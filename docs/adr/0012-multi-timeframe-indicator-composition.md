# ADR 0012 — Multi-Timeframe Indicator Composition

## Status

Accepted (Milestone 1.2)

## Context

Milestone 0.9 produced a no-lookahead multi-timeframe candle decision feed. Milestone 1.1 / 1.1A produced provenance-sealed, prefix-safe indicator decision feeds. Adaptive Multi-Timeframe Trend Breakout still needs both candle histories and indicators at each execution-bar decision, but strategy signal rules remain deferred.

Providers must not receive complete offline indicator series (which include future values) or run-level hashes that commit to those complete series. Context indicators must follow exact-close alignment (`latest_closed_index`), never the execution bar index.

## Decision

1. **Composition input is provenance-sealed.** `MultiTimeframeIndicatorInput.from_verified` rebuilds the trusted `MultiTimeframeBacktestInput`, rebuilds every configured `IndicatorSeriesBundle`, binds each bundle to the exact corresponding MTF candle tuple (`candles is` identity plus symbol/TF/count/hash), and computes a run-level `indicator_composition_hash`. Callers cannot supply composition hashes, ordering, counts, or readiness.

2. **Full indicator bundle hashes are run-level only.** The composition hash binds the MTF input bundle hash plus ordered execution/context indicator bundle hashes (or null). It must not appear on provider-visible decision views because it commits to complete offline indicator series, including values beyond the current decision bar.

3. **Providers receive bounded prefix-safe views.** `MultiTimeframeIndicatorDecisionFeed.view_at(i)` composes the existing MTF candle view with optional execution and context `IndicatorDecisionView` objects. Prefix chains are built once at feed creation; `view_at` performs no indicator recalculation, prefix reconstruction, realignment, or bundle rebuild.

4. **Context indicators use `latest_closed_index`.** When no context candle is closed, the context indicator view is `None` and readiness is false. When closed, the feed calls `context_indicator_feed.view_at(latest_closed_index)` — never the execution index.

5. **Candle and indicator readiness are separate gates.** Overall composed readiness requires base candle readiness **and** every configured execution indicator view ready **and** every configured context indicator view present and ready. Unconfigured slots (`None`) do not block.

6. **Existing engine and MTF contracts remain unchanged.** The indicator-aware adapter implements `BacktestDecisionProvider` and drives the unchanged `BacktestEngine` on trusted execution candles. Existing `MultiTimeframeProviderAdapter`, `StrategyBacktestEnvelope` schema/hash, and MTF goldens are preserved.

7. **Envelope wrapping preserves schema compatibility.** `IndicatorStrategyBacktestEnvelope` wraps the existing `StrategyBacktestEnvelope` and adds an indicator-aware envelope hash binding `(schema, base.envelope_hash, composition_hash)`. No raw-hash constructor is permitted.

8. **Optional indicator slots are explicit `None` values.** Context indicator configuration is an exact tuple aligned with MTF context count. Explicit `None` distinguishes “unconfigured (non-blocking)” from “configured but not yet ready.”

## Consequences

- Milestone 1.3+ strategy providers can consume `MultiTimeframeIndicatorDecisionView` without lookahead or forged provenance.
- Adaptive MTF / Support and Resistance signal rules, ATR stops, persistence, API, and UI remain deferred.
- New composition and envelope hashes are additive; existing Milestone 1.1 view hashes and MTF hashes must remain unchanged.
