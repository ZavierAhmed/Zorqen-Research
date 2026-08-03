# ADR 0002 — Core registry and audit persistence

- Status: Accepted
- Date: 2026-08-03
- Milestone: 0.2

## Context

Zorqen Research needs durable metadata for the approved initial strategy families and an append-only application audit trail before any executable strategy definitions, campaigns, or backtests exist.

## Decisions

### Strategy-family metadata is separated from executable definitions

The `strategy_families` table records identity, display name, description, research priority, and status only. It does not store indicators, parameters, timeframes, entry/exit logic, or candidate definitions. Those belong to later milestones after authoritative baselines are approved.

### Seed IDs are stable

Canonical families use fixed UUIDs:

- `adaptive_mtf_trend_breakout` → `a1b2c3d4-e5f6-4789-a012-3456789abc01`
- `support_resistance` → `a1b2c3d4-e5f6-4789-a012-3456789abc02`

Stable IDs keep references consistent across environments, migration downgrade/re-upgrade cycles, and future foreign keys.

### Audit events are append-only at the application layer

`AuditEventRepository` and `AuditEventService` expose only append. There is no update or delete API. Database-level revoke of UPDATE/DELETE is deferred; application-level enforcement is sufficient for Milestone 0.2 and is covered by tests.

### PostgreSQL JSONB for audit payloads

JSONB stores structured context without inventing per-event tables. It preserves queryability and round-trips nested objects for correlation and later analytics.

### Mutation APIs are deferred

Strategy-family HTTP endpoints are read-only (`GET` list and get-by-code). Registry changes happen through migrations/seeds, not operators editing families via the API in this milestone.

### Migrations run through a dedicated Compose service

A one-shot `migrate` service runs `alembic upgrade head` after PostgreSQL is healthy and before API/worker start (`service_completed_successfully`). This avoids embedding schema upgrades inside every process and keeps repeated `docker compose up` idempotent via Alembic revision tracking.

## Consequences

- Operators can discover approved research families without implying executable strategies exist.
- Audit append can be used by later features without redesigning process boundaries.
- Clean-volume Compose startup applies schema and seeds before the API serves registry routes.
