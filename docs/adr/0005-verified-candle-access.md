# ADR 0005 — Verified Candle Access and Querying

## Status

Accepted (Milestone 0.5)

## Context

Published datasets already store content-addressed canonical CSV partitions and manifests. Backtesting and research components must consume trusted candles without reading arbitrary filesystem paths, fabricating missing fields, or silently accepting non-canonical bytes. The local architecture fixture remains a six-column manifest-v1 artifact with a frozen content hash.

## Decision

1. **Every query revalidates immutable data.** Before returning candles, the application rebuilds and hashes the canonical manifest, verifies partition and provenance metadata, verifies raw source-page artifacts and the normalized partition through the artifact store, parses CSV into domain `Candle` values, and requires byte-for-byte reserialization equality. Cached unverified pages are not used.
2. **The application owns the reader contract.** `CandlePartitionReader` lives in the application layer. Infrastructure provides `LocalCandlePartitionReader`. API routes and CLI call `CandleQueryService`; they do not open artifact keys as filesystem paths.
3. **Only manifest-v2 canonical Binance imports are queryable.** Supported datasets require `manifest_version=2`, provider `binance`, market `binance_futures`, data type `contract_klines`, canonical schema version `1`, and `text/csv` partitions.
4. **The legacy fixture is not upgraded by fabrication.** Manifest-v1 fixture bytes and hash remain unchanged. Candle query returns a distinct unsupported-schema error. A future governed migration may publish a new canonical derivative without altering the original artifact.
5. **Canonical reserialization is required.** Semantically valid but non-canonical CSV (CRLF, BOM, trailing zeroes, alternate timestamp forms, missing final newline, etc.) is rejected so one logical sequence has one byte representation.
6. **Decimals are returned as strings.** JSON floating-point would lose precision. Candle API fields serialize finite `Decimal` values as canonical decimal strings; timestamps use `Z` UTC; `trade_count` remains an integer.
7. **Pagination uses exclusive open-time cursors.** Responses include at most `limit` candles, peek one ahead for `has_more`, and set `next_cursor` to the last returned open time. Offset pagination is avoided because it is unstable for immutable sequences and invites skip/duplicate bugs.
8. **Parquet and caching are deferred.** Full-artifact read and verification before serving a page is acceptable within the existing import-size guardrail. Unbounded process-global caches and Parquet/indexed access are out of scope.
9. **Read operations are not audited.** Ordinary candle queries and `verify-snapshot` do not append audit events and do not mutate datasets. Publication remains the audited boundary.

## Consequences

- Future backtesters can depend on a verified read path without implementing their own integrity checks.
- Operators can verify a snapshot with `zorqen-dataset verify-snapshot` without network access.
- Unsupported legacy fixtures remain listable via dataset APIs while candle query stays closed until a governed migration.
