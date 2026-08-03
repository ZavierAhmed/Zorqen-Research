# ADR 0007 — Immutable Strategy Definitions

## Status

Accepted (Milestone 0.7)

## Context

Strategy-family metadata exists, and the backtest kernel is strategy-independent. Executable research still needs a formal, deterministic description of what a strategy *is* before any algorithm, provider factory, or persistence is introduced.

## Decision

1. **Pure immutable schema.** Strategy definitions, parameter schemas, bound parameter sets, and instance specifications are frozen domain objects with no FastAPI, SQLAlchemy, HTTP, Binance, indicator, or dynamic-import dependencies.
2. **Exact family identity binding.** `family_id` and `family_code` must be one seeded pair from the existing strategy-family domain constants. Mismatched or unknown pairs fail.
3. **Strict semantic versions.** Versions are `MAJOR.MINOR.PATCH` with no prefixes, prerelease, build metadata, or leading zeroes.
4. **Canonical identifiers.** Definition codes and parameter keys use lower_snake_case with a fixed regex and length bound.
5. **Typed parameters.** Decimal, integer, boolean, and enum kinds are discriminated. Decimals reject floats/bools/ints and use exact step alignment. JSON decimals are canonical strings.
6. **Ordered structure.** Parameters are lexicographic by key. Context timeframes ascend by duration. Directions are `long` then `short`. Non-canonical ordering is rejected, not silently repaired.
7. **Draft vs approved.** Drafts may omit `source_spec_sha256`. Approved definitions require a 64-character lowercase hex source hash. Approved does **not** mean executable code exists.
8. **Canonical hashing.** Definition, parameter-set, and instance hashes are SHA-256 over compact sorted-key JSON bytes with no timestamps, paths, hosts, or module/class references.
9. **Strict parsing.** UTF-8 only, no BOM, duplicate keys rejected, unknown fields rejected, size-capped, non-finite JSON constants rejected.
10. **Deferred execution and persistence.** No provider factory, strategy logic, Alembic tables, HTTP endpoints, or UI in this milestone.

## Consequences

- Future executable strategies must satisfy this schema before any backtest wiring.
- Test fixtures under `tests/fixtures/strategy_definitions/` are draft-only and are not production baselines.
- Persistence and execution bridges remain later milestones.
