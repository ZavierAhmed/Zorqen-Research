# ADR 0006 — Deterministic Bar-Based Backtest Kernel

## Status

Accepted (Milestone 0.6)

## Context

Verified candle access exists, but execution semantics for research qualification must be proven independently of strategies, databases, and network I/O. The first kernel must be small, exact, and reproducible.

## Decision

1. **Strategy-independent kernel.** The engine depends only on a `BacktestDecisionProvider` protocol. Scripted providers exist for golden tests; no strategy-family logic is implemented.
2. **Decide at close, fill at next open.** Intents generated at candle close never use that candle’s OHLC for fills. Market intents become eligible only at the next candle open, preventing same-bar lookahead.
3. **Market orders only.** Limit, stop-entry, maker, and partial fills are deferred so fill semantics remain unambiguous.
4. **Stop-first same-bar ambiguity.** When stop and target are both touched in one candle, the kernel closes at the stop. Intrabar path reconstruction is not attempted.
5. **Decimal-only economics.** Fees, slippage, prices, quantities, and P&L use finite `Decimal` math with documented tick/quantity alignment. Binary floats are rejected.
6. **Deterministic IDs and serialization.** Fill, position, and trade IDs are sequential strings. Canonical JSON excludes hostnames, clocks, paths, and random UUIDs so result hashes are stable.
7. **Adverse slippage on every fill.** Entry, explicit exit, stop, take-profit, and end-of-data fills apply adverse market slippage and taker fees.
8. **Accounting without double-counting.** Entry fees are deducted when the entry fills. Exit applies gross P&L and deducts the exit fee. Final equity equals initial equity plus net P&L.
9. **Realized-equity drawdown only.** Maximum drawdown is computed from the realized equity curve after fees/P&L updates. Mark-to-market intratrade drawdown is deferred.
10. **No persistence or API yet.** The kernel is pure in-memory. HTTP endpoints, Alembic tables, workers, and UI for backtests are out of scope.

## Consequences

- Golden scenarios and `zorqen-backtest run-golden` prove execution semantics before any strategy work.
- Later milestones can add indicators/strategies without rewriting fill math.
- Portfolio, leverage, funding, and limit/maker execution remain explicitly unsupported.
