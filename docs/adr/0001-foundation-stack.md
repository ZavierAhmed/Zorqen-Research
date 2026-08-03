# ADR 0001 — Foundation stack

- Status: Accepted
- Date: 2026-08-03
- Milestone: 0.1

## Context

Zorqen Research needs a clean executable repository foundation before any strategy research behavior is implemented. The system must support Windows development, Windows/Linux VPS deployment, CPU-first operation, and a modular monolith with separate API and worker processes.

## Decisions

### Python 3.12 and FastAPI

Python 3.12 is the required runtime. FastAPI provides typed HTTP APIs, OpenAPI documentation, and a clean application-factory pattern suitable for health probes and later research APIs. Pydantic v2 and pydantic-settings supply validated configuration from `ZORQEN_` environment variables.

### PostgreSQL and Alembic

PostgreSQL is the system of record. SQLAlchemy 2.x with asyncpg serves the application; Alembic manages schema migrations. Milestone 0.1 ships an empty baseline revision only — no campaign, strategy, backtest, or candidate tables.

### React, Vite, and TypeScript

The operator UI is a React + Vite + TypeScript frontend with strict TypeScript, ESLint, Vitest, and React Testing Library. The initial page is a restrained system-status view only.

### Modular monolith

One Python package (`zorqen_research`) owns API, worker, core configuration, and infrastructure adapters. This avoids premature microservices while preserving clear module boundaries.

### Separate API and worker processes

The API process serves HTTP. The worker process runs independently (`python -m zorqen_research.worker`) with a one-shot `--check` mode. Separating processes keeps long-running work out of the request path and matches the intended future job model.

### CPU-first design

No GPU or CUDA dependency is required or declared. Research workloads in later milestones must remain runnable on CPU-only hosts.

### Windows and Linux portability

Configuration uses environment variables and `pathlib`. No Windows drive letters are hardcoded. Direct Windows development (PowerShell + local PostgreSQL/Docker) and Docker Compose are both supported.

### Deferred database-backed worker coordination

Job leasing, campaign scheduling, and research experiment processing are intentionally deferred. The worker currently idles with clean shutdown handling so later milestones can introduce coordination without rewriting process boundaries.

## Consequences

- Foundation verification can proceed without inventing domain schema.
- Later milestones can add tables, routes, and worker jobs inside existing process boundaries.
- Operators can confirm API, worker, database, frontend, CI, and Docker plumbing before research logic exists.
