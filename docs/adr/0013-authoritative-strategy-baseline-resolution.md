# ADR 0013 — Authoritative Strategy Baseline Resolution

## Status

Accepted (Milestone 1.3)

## Context

Zorqen Research must not invent Adaptive Multi-Timeframe Trend Breakout behavior. The master-spec illustration JSON is not executable authority. MOMO Quant at a pinned commit is the only executable source for this family’s production semantics.

Milestone 1.3 must freeze a machine-readable baseline contract, source-evidence manifest, parity fixtures, and an approved `StrategyDefinition` only when every protected execution semantic is evidenced. Strategy provider implementation remains deferred to Milestone 1.4.

## Decision

1. **Authority hierarchy.** Executable MOMO production code and tests at commit `766e31db73bbb130d12ba84f1568745210db6155` outrank frozen seeds, informational defaults, documentation, and the master-spec illustration.
2. **Resolution statuses.** `RESOLVED`, `UNRESOLVED`, `CONTRADICTORY`, and `NOT_IMPLEMENTED_IN_MOMO` are the only allowed outcomes. `RESOLVED` requires empty `unresolved_items` and authoritative evidence for every protected semantic.
3. **Artifacts.** Checked-in files live under `baselines/adaptive_mtf_trend_breakout/v1/` (`baseline_contract.json`, `source_evidence.json`, `approved_definition.json`) plus `tests/fixtures/adaptive_mtf_trend_breakout/v1/`.
4. **Canonical hashing.** Contract, evidence, fixture expected traces, and the approved definition use UTF-8 compact sorted-key JSON. The approved definition’s `source_spec_sha256` equals the baseline-contract hash.
5. **No provider.** Milestone 1.3 must not register or implement an Adaptive MTF strategy provider and must not modify MOMO Quant.
6. **CLI gate.** `zorqen-strategy verify-baseline --family adaptive_mtf_trend_breakout` verifies internal consistency and reports `provider_implementation_allowed` only when status is `RESOLVED`.

## Consequences

- Milestone 1.4 may propose provider implementation and cross-engine parity against these frozen artifacts.
- Illustrative master-spec fields that differ or are unimplemented remain documented in `master_spec_comparison` without rewriting MOMO or the PDF.
- Preferred seed execution is `5m` → context `1h`; evaluator warmups are `165` / `205`, distinct from the data-requirement profile of `600` bars.
