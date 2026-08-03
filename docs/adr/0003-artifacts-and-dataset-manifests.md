# ADR 0003 — Artifacts and dataset manifests

- Status: Accepted
- Date: 2026-08-03
- Milestone: 0.3

## Context

Future market-data imports need durable identity for large candle files and a
verifiable metadata record. Storing candle payloads in PostgreSQL would bloat
the system of record and couple query patterns to blob storage.

## Decisions

### Large data stays outside PostgreSQL

PostgreSQL stores dataset snapshot and partition metadata only: identity,
status, hashes, row counts, ranges, validation summaries, and artifact keys.
Immutable bytes live in a local content-addressed artifact store under
`ZORQEN_ARTIFACT_ROOT`.

### SHA-256 content addressing

Artifact keys derive from SHA-256 of file bytes (`sha256/ab/cd/<digest>`).
Identical bytes reuse the same key. Different bytes cannot share a key.
Filenames are never storage identity.

### Atomic publication

Writes go to a temporary file under the artifact root, are flushed, then moved
into the final key with an atomic replace. Partial final objects are not
exposed. Temporary files are cleaned after failure. Concurrent identical
publishes are safe.

### Canonical immutable manifests

A published snapshot has a deterministic JSON manifest with stable key and
partition ordering and UTC timestamps. The stored `content_hash` is SHA-256 of
the logical canonical payload (dataset name, exchange, ordered partitions,
totals, ranges, validation summary, and manifest version). Publication identity
fields (`dataset_snapshot_id`, `publication_timestamp`) remain in the document
but are excluded from the digest so identical logical content is stable across
idempotent fixture republication. Published snapshots are immutable through
application services.

### Fixture ingestion precedes network ingestion

A deterministic local CSV fixture proves artifact storage, partition metadata,
manifest hashing, transactional audit append, and read-only APIs without Binance
or any external market-data access.

### No mutation or upload API yet

HTTP endpoints are read-only (`GET` list, detail, manifest). Fixture publication
is an explicit CLI / Compose one-shot. There is no general file-upload,
dataset-update, or delete API in this milestone.

### Published snapshots cannot change

Status transitions forbid republishing, modifying published rows through
services, or publishing rejected snapshots. Draft and rejected snapshots are
hidden from public list/detail/manifest routes.

## Consequences

- Later importers can attach Parquet/CSV artifacts without redesigning metadata.
- Operators can verify datasets by hash without trusting local paths.
- Clean-volume Compose startup still does not auto-publish fixtures.
