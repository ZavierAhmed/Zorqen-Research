# ADR 0007 — Immutable Strategy Definitions

## Status

Accepted (Milestone 0.7); integrity boundaries hardened (0.7A); semantic binding + Ubuntu nesting gate (0.7B)

## Context

Strategy-family metadata exists, and the backtest kernel is strategy-independent. Executable research still needs a formal, deterministic description of what a strategy *is* before any algorithm, provider factory, or persistence is introduced.

Milestone 0.7 left three trust-boundary gaps: caller-supplied logical hashes that could be forged, a mutable seeded-family mapping, and incomplete conversion of adversarial JSON/Unicode failures into the documented parser error boundary.

Milestone 0.7A closed those three gaps but left two further defects: (1) `StrategyInstanceSpecification` accepted parameter sets that only matched `definition_hash` without revalidating keys/kinds/bounds against the definition schema; (2) Ubuntu Quality failed because deep-nesting rejection depended on OS stack `RecursionError` rather than an explicit depth gate.

## Decision

1. **Pure immutable schema.** Strategy definitions, parameter schemas, bound parameter sets, and instance specifications are frozen domain objects with no FastAPI, SQLAlchemy, HTTP, Binance, indicator, or dynamic-import dependencies.
2. **Exact family identity binding.** `family_id` and `family_code` must be one seeded pair from the existing strategy-family domain constants. Mismatched or unknown pairs fail.
3. **Immutable seeded-family policy.** `SEEDED_FAMILY_PAIRS` is a runtime-immutable mapping (`MappingProxyType` over a private tuple of exactly two pairs). Runtime assignment, deletion, or third-family insertion fails; `require_seeded_family_pair()` cannot be influenced by external mutation.
4. **Strict semantic versions.** Versions are `MAJOR.MINOR.PATCH` with no prefixes, prerelease, build metadata, or leading zeroes.
5. **Canonical identifiers.** Definition codes and parameter keys use lower_snake_case with a fixed regex and length bound.
6. **Typed parameters.** Decimal, integer, boolean, and enum kinds are discriminated. Decimals reject floats/bools/ints and use exact step alignment. JSON decimals are canonical strings. Enum choices/defaults/bound values must be real `str` Unicode scalars (not arbitrary objects with custom equality).
7. **Unicode scalar text.** All free-text fields included in canonical UTF-8 serialization must be valid Unicode scalar values (no NUL; no lone surrogates U+D800–U+DFFF). Accepted models must always serialize without raw `UnicodeEncodeError`.
8. **Ordered structure.** Parameters are lexicographic by key. Context timeframes ascend by duration. Directions are `long` then `short`. Non-canonical ordering is rejected, not silently repaired.
9. **Draft vs approved.** Drafts may omit `source_spec_sha256`. Approved definitions require a 64-character lowercase hex source hash. Approved does **not** mean executable code exists.
10. **Computed hashes.** The definition hash is produced only by `hash_definition()` over canonical definition bytes. Parameter-set and instance hashes are `init=False` computed fields (`parameter_set_hash`, `instance_hash`) — never caller-writable. Parameter-set hash covers `{definition_hash, parameters}` and does not include itself. Instance hash covers `{definition_hash, parameter_set_hash}`.
11. **Semantic parameter-set revalidation.** `validate_parameter_set_against_definition()` verifies hash match, exact key set/order, per-parameter `validate_value()`, equality of validated vs stored values, and recomputed `parameter_set_hash`. `StrategyInstanceSpecification.__post_init__` runs this before computing `instance_hash`. Direct construction cannot bypass `bind_parameter_values()` semantics.
12. **Strict SHA-256 shape.** Logical hashes must be exactly 64 lowercase hex characters; all-zero placeholders are rejected for computed logical hashes.
13. **Strict parsing.** UTF-8 only, no BOM, duplicate keys rejected, unknown fields rejected, size-capped, non-finite JSON constants rejected. Huge integer tokens, nesting beyond `MAX_JSON_NESTING_DEPTH` (platform-independent walk), residual `RecursionError`, and relevant `OverflowError`/`ValueError` cross the `StrategyDefinitionParseError` boundary without path or traceback leakage. `MemoryError` is not caught.
14. **Deferred execution and persistence.** No provider factory, strategy logic, Alembic tables, HTTP endpoints, or UI in this milestone.

## Consequences

- Future executable strategies must satisfy this schema before any backtest wiring.
- Test fixtures under `tests/fixtures/strategy_definitions/` are draft-only and are not production baselines.
- Persistence and execution bridges remain later milestones.
- Callers cannot forge definition/parameter-set/instance hash relationships through public constructors.
- A matching `definition_hash` alone is insufficient to attach a parameter set to a definition.
- Nesting limits are deterministic across Windows and Ubuntu CI runners.
