# ADR 0003 — Artifacts and dataset manifests

- Status: Accepted (amended by Milestone 0.3A)
- Date: 2026-08-03
- Milestone: 0.3 / 0.3A

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

### Atomic no-clobber publication

Writes go to a temporary file under the artifact root and are flushed/`fsync`ed.
The final object path is created with an atomic hard-link (`os.link`) that fails
if the destination already exists. Existing object files are never replaced or
truncated. When the destination already exists, the store verifies bytes and
either reuses identical content or raises a sanitized collision error.

Metadata files use the same no-clobber hard-link rule.

### Metadata: first successfully persisted wins

Descriptive fields (media type, original filename) are not content identity.
The first metadata record that successfully persists for a key wins. Later
publishers with different descriptive fields do not replace it. Every
`publish_bytes` / `publish_file` return value is reloaded and verified from
disk via `get_metadata`.

### Metadata verification

`get_metadata` verifies the persisted record against the content-addressed key
and the actual object bytes (key, SHA-256, size, supported media type, filename
type, timezone-aware timestamp). Corruption is rejected with a sanitized error
and is never silently rewritten.

If an object exists without metadata, `get_metadata` raises a sanitized
“metadata is missing” error. A subsequent `publish_bytes` call may create
metadata with no-clobber semantics (recovery).

### Symlink containment

The configured artifact root itself must not be a symlink; the store expands the
user path and rejects symlink roots before resolving. The `objects`, `meta`,
and `tmp` directories must also be real directories (not symlinks) remaining under
the resolved artifact root. Nested path components and final object/metadata
paths that are symlinks are rejected.

### Orphan objects after database rollback

Object publication occurs before the dataset database transaction commits. A
failed DB transaction may leave an unreferenced immutable object in the
artifact store. No partial snapshot or audit event remains. Content-addressed
orphans are harmless and reusable. Mark-and-sweep garbage collection of
unreachable objects is deferred to a separately governed maintenance process
and is not implemented here.

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
