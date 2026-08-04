# ADR 0011 — No-Lookahead Bounded Indicator Views

## Status

Accepted (Milestone 1.1)

## Context

Milestone 1.0 / 1.0A produced complete offline `IndicatorSeries` objects. Those series contain every calculated value for the full input candle tuple, including values that would be “future” relative to an individual backtest decision bar. Passing a complete series into a strategy provider would allow ordinary indexing, slicing, iteration, `repr`, or accidental length inspection to leak lookahead.

Adaptive Multi-Timeframe Trend Breakout still needs indicator values at decision time, but Milestone 1.1 only introduces a **standalone** single-timeframe visibility layer. Composition with `MultiTimeframeDecisionFeed` remains Milestone 1.2.

## Decision

1. **Offline bundle, provider-safe views.** `IndicatorSeriesBundle.from_verified` accepts one exact `IndicatorInput` and a tuple of calculator-produced `IndicatorSeries`, reverifies result hashes, rejects duplicate canonical keys, and retains complete series offline. Bundles must not be passed to strategy providers.

2. **Feed → bounded view.** `IndicatorDecisionFeed.from_bundle` binds internal `_VerifiedIndicatorSource` objects once and precomputes prefix hash chains once. `view_at(bar_index)` returns an `IndicatorDecisionView` whose items expose only `VisibleIndicatorHistory` for `values[0:bar_index+1]`.

3. **Prefix-only content hashes.** Provider-visible hashes must not depend on hidden future values.

   - Header (canonical compact JSON): `schema_version`, `symbol`, `timeframe`, `indicator_code`, `parameters`, `math_policy`.
   - Excluded from the header: full input candle hash, full input hash, full series result hash, total future value count, dataset snapshot ID, generated timestamp.
   - Chain:
     - `H0 = SHA256(canonical_header_bytes)`
     - `H(i+1) = SHA256(raw_bytes(H(i)) + b"\n" + canonical_value_token(value[i]))`
   - Tokens: `None → b"null"`; `Decimal →` UTF-8 canonical decimal bytes (signed zero → `"0"`).
   - `prefix_hashes[0]` covers zero visible values; `prefix_hashes[N]` covers values `0..N-1`.
   - View construction retrieves the hash in O(1).

4. **Decision-view hash.** Includes only schema version, symbol, timeframe, bar index, visible count, item keys, readiness, and visible-prefix hashes. Full result/input hashes are excluded so future appends cannot alter earlier decision-view hashes.

5. **Warmup / readiness.** Undefined warmup slots remain `None`. An item is `ready` iff the latest visible value is an exact `Decimal`. Overall readiness requires every item ready.

6. **Constant-time construction.** Feed preparation is O(n) per series once. `view_at` is O(number of indicators) and independent of bar index: no indicator recalculation, no prefix rescanning, no value-prefix slicing or copying.

7. **Safe representation.** Histories, items, views, and internal sources must not reveal future values, source length, or full result hashes in `repr` / `str`.

8. **Deferred work.** MTF/provider composition, persistence, caching, APIs, UI, and strategy signal logic remain deferred. Existing MTF feed/view/provider/context types are unchanged.

## Consequences

- Strategy providers in later milestones consume `IndicatorDecisionView` / `VisibleIndicatorHistory`, never complete `IndicatorSeries` or bundles.
- Milestone 1.2 may compose this feed with multi-timeframe alignment without changing the prefix-hash contract.
- Adding indicators still requires explicit codes, calculators, goldens, and tests — not a plugin framework.
