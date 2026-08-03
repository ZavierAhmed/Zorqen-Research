# Zorqen Research - Project Status

> This file records verified repository reality for handoff between coding agents. It must be updated in every milestone commit. Git, tests, and implementation remain authoritative when this file is stale or incorrect.

## 1. Project Identity

- Product: Zorqen Research
- Repository: Not created yet
- Default branch: Not established
- Current branch: Not established
- Latest authoritative commit: None
- Master specification: Zorqen Research Master Specification v0.1
- Current environment: Windows development laptop
- Target deployment: Windows or Linux VPS
- Runtime principle: CPU-first; no mandatory GPU dependency

## 2. Product Purpose

Zorqen Research is a separate autonomous strategy-research and qualification platform. It creates controlled candidates, runs deterministic testing and validation, applies hard gates and qualification scoring, and exports qualified packages to MOMO Quant.

It does not connect to exchanges, place paper/live trades, approve live deployment, modify MOMO Quant, or use unrestricted strategy code generation in the MVP.

## 3. Initial Strategy Scope

### Primary

- Adaptive Multi-Timeframe Trend Breakout

### Secondary

- Support and Resistance

Baseline behavior for both strategies must come from an authoritative implementation or explicitly approved formal definition before autonomous modification begins.

## 4. Current Milestone

- Milestone: Planning / pre-repository
- Status: Product direction defined
- Objective: Finalize the master specification and prepare the first repository-bootstrap prompt
- Implementation started: No
- Repository commit created: No

## 5. Latest Verified State

- Backend: Not created
- Frontend: Not created
- Worker: Not created
- Database: Not created
- Tests: Not created
- Migrations: Not created
- Build status: Not applicable

## 6. Frozen Product Decisions

- Umbrella brand: Zorqen
- New application: Zorqen Research
- Existing execution platform: MOMO Quant for now
- Future possible execution name: Zorqen Quant
- Separate repository, database, and deployment from MOMO Quant
- Initial strategy families: Adaptive MTF Trend Breakout and Support and Resistance
- Research authority only; no paper/live trading
- Candidate-package file integration before API integration
- One master PDF plus `AGENTS.md` and this status file
- Milestone-based coding with loop prompting and independent review after every commit

## 7. Architecture Direction

Recommended initial stack:

- Python 3.12
- FastAPI and Pydantic
- PostgreSQL and Alembic
- Dedicated Python worker using database-backed job leasing
- React, Vite, and TypeScript
- pytest, Hypothesis, Vitest, and Playwright
- Ruff and static type checking
- Docker Compose plus direct Windows commands
- Filesystem artifact store behind an abstraction
- Parquet for large tabular artifacts and JSON for contracts

This remains planning guidance until implemented and verified.

## 8. Research Engine Status

- Campaign model: Not implemented
- Strategy DSL: Not implemented
- Data snapshots: Not implemented
- Backtest engine: Not implemented
- Validation: Not implemented
- Qualification policy: Not implemented
- Candidate packages: Not implemented
- MOMO Quant integration: Not implemented

## 9. Outstanding Work

1. Create the repository-foundation coding prompt.
2. Bootstrap API, worker, frontend, database migrations, tests, CI, and documentation.
3. Review the first coding-agent commit independently.
4. Define the next milestone from repository evidence.
5. Formalize authoritative baselines for both strategies in later milestones.

## 10. Known Risks

- Baseline strategy logic has not yet been imported or formalized.
- Final qualification thresholds require calibration.
- AI model/provider for structural hypothesis generation is not selected.
- MOMO Quant import API is not designed.
- No implementation evidence exists yet.

## 11. Next Authorized Work

Create the first coding-agent bootstrap prompt for the repository foundation only.

The first coding agent must not implement strategy logic, backtesting, autonomous research, candidate scoring, MOMO Quant integration, or paper/live trading.

## 12. Coding-Agent Handoff

A future coding agent must read:

1. `README.md`
2. `AGENTS.md`
3. `PROJECT_STATUS.md`
4. Active milestone prompt
5. Git status, branch, recent log, and diff
6. Relevant tests
7. Relevant implementation files

Because the repository does not exist yet, no setup or verification commands have been executed.

## 13. Change Log

| Date | Milestone | Commit | Summary | Verification |
|---|---|---|---|---|
| 2026-08-03 | Planning | None | Product direction and master specification v0.1 established | Document-level only |
