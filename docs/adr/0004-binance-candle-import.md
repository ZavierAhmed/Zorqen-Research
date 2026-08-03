# ADR 0004 — Canonical Binance Futures Candle Import

## Status

Accepted (Milestone 0.4); corrected by Milestones 0.4A and 0.4B

## Context

Zorqen Research needs a controlled path to acquire real historical market data for later research milestones. The first importer must remain inside the product boundary: public market data only, no trading, no account access, and no silent mutation of published datasets.

## Decision

1. **Public REST only.** Use Binance USDⓈ-M Futures public klines (`GET /fapi/v1/klines` on `https://fapi.binance.com`). No API keys, secrets, signed requests, or private endpoints are accepted or implemented.
2. **Application owns the market-data client contract.** `MarketDataClient` lives in the application layer. `BinanceImportService` depends on that protocol. The HTTPX `BinanceFuturesPublicClient` is an infrastructure implementation that structurally satisfies the protocol. Application modules do not import infrastructure page-limit or host constants solely to obtain the contract.
3. **Exact fixed production origin.** Production requests always target `https://fapi.binance.com`. The HTTP client does not accept a public `base_url` override, environment origin setting, or `.binance.local` wildcard. Tests inject `httpx.MockTransport` against the production origin rather than alternate hosts.
4. **Strict half-open closed ranges.** Imports use `[start, end)` with timeframe-aligned UTC bounds. Misaligned values are rejected (not rounded). Ranges that would include the currently open candle are rejected. Incomplete candles are never published as historical research data.
5. **Complete coverage is mandatory.** Expected candle count must match actual count, and adjacent open times must advance by exactly one timeframe duration. Gaps, duplicates, and out-of-order candles fail the import. No interpolation, synthetic OHLCV, or “allow gaps” switch exists in this milestone.
6. **Canonical CSV is the source artifact.** Normalized candles are serialized to deterministic UTF-8 CSV (`text/csv`, `\n` endings). Identical logical candles produce identical bytes and therefore identical content-addressed keys. Parquet is deferred until the canonical source format is stable.
7. **Raw pages are preserved.** Every successful Binance page response is stored as an immutable JSON artifact with request metadata in the manifest provenance. Failed or rolled-back imports may leave unreferenced content-addressed orphans under the existing artifact consistency model.
8. **CI uses mocked transport.** GitHub Actions and local integration tests inject deterministic HTTPX `MockTransport` responses. CI must not depend on Binance uptime or regional availability.
9. **Live verification is optional and separate.** A small public live smoke import may be run manually when network access exists. It is never part of CI.
10. **Source drift conflicts instead of replacement.** The same import identity with different logical content raises a duplicate/conflict error. Published snapshots are never silently rewritten.
11. **Manifest version 2 for imports.** Binance imports publish manifest version `2` with stable provenance. The existing local fixture retains manifest version `1` and its frozen content hash.
12. **Canonical candle UTC policy.** Naive timestamps and non-zero UTC offsets are rejected at the domain boundary. Infrastructure converters must produce zero-offset UTC before constructing `Candle`.
13. **Finite decimals only.** `parse_decimal` and `Candle` reject NaN / ±Infinity. Non-finite Binance fields surface as sanitized `BinanceResponseError`.
14. **Trade count is a non-negative integer.** Canonical `Candle.trade_count` rejects booleans and non-integer types. The Binance parser converts invalid trade-count fields into sanitized `BinanceResponseError`.

## Consequences

- Operators can import approved symbols/timeframes via CLI or an explicit Docker Compose profile without credentials.
- Research integrity starts at acquisition: closed candles, full coverage, and immutable artifacts.
- Application/infrastructure dependency direction remains testable with fake protocol clients and MockTransport.
- Later milestones may add candle query, resampling, Parquet derivatives, and strategies without changing this acquisition contract.
