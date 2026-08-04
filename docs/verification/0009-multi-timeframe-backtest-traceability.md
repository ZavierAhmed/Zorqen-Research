# 0009 — Multi-Timeframe Backtest Decision Feed Traceability

Milestone: **0.9 — Deterministic Multi-Timeframe Backtest Decision Feed**  
Base commit: `3ac02582af357cf91a3080149abf470d2f60222c`

Evidence classes: `PROVEN BY AUTOMATED TEST` · `VERIFIED BY SOURCE INSPECTION` · `NOT TESTED` · `NOT APPLICABLE`

## Acceptance matrix

| Requirement | Implementation | Automated test | Result |
|---|---|---|---|
| Factory-bound MTF input bundle | `MultiTimeframeBacktestInput.from_verified` | `test_bundle_rejects_*`, forged construction | PROVEN BY AUTOMATED TEST |
| Definition TF/context exact match | input factory | `test_bundle_rejects_missing_extra_unsorted_duplicate_context` | PROVEN BY AUTOMATED TEST |
| No-context definitions rejected by MTF runner | input factory | `test_bundle_rejects_no_context_definition_and_forged_construction` | PROVEN BY AUTOMATED TEST |
| Computed hashes / alignments only | input factory + alignment factories | bundle tests + goldens | PROVEN BY AUTOMATED TEST |
| Visible history bounds / no future access | `VisibleCandleHistory` | `test_visible_history_bounds_and_no_future_access`, red-team | PROVEN BY AUTOMATED TEST |
| Decision feed indexes / exact-close / determinism | `MultiTimeframeDecisionFeed.view_at` | `test_decision_feed_indexes_readiness_and_determinism` | PROVEN BY AUTOMATED TEST |
| Warmup readiness + provider skip | adapter + runner | `test_adapter_warmup_direction_and_runner_envelope`, `test_warmup_zero_still_requires_closed_context` | PROVEN BY AUTOMATED TEST |
| Unsupported direction fails without fill | adapter | `test_adapter_warmup_direction_and_runner_envelope` | PROVEN BY AUTOMATED TEST |
| Provider list/exception sanitization | adapter + engine boundary | `test_provider_list_output_and_exception_sanitization` | PROVEN BY AUTOMATED TEST |
| Envelope binds identities; forged construction fails | `StrategyBacktestEnvelope` | `test_envelope_hash_sensitivity_to_parameters_and_context` | PROVEN BY AUTOMATED TEST |
| Frozen MTF goldens A–E | `goldens.py` + CLI | `zorqen-backtest run-mtf-golden`, red-team CLI | PROVEN BY AUTOMATED TEST |
| Existing seven result hashes unchanged | `BacktestEngine` untouched | `zorqen-backtest run-golden` | PROVEN BY AUTOMATED TEST |
| Existing alignment/resample hashes unchanged | no 0.8A contract change | `zorqen-timeframes verify-golden` | PROVEN BY AUTOMATED TEST |
| No strategy algorithms / persistence / API | package layout | Source inspection | VERIFIED BY SOURCE INSPECTION |
| No new migration | alembic versions | Verification (0001–0003 only) | VERIFIED BY SOURCE INSPECTION |

**Summary: NOT TESTED: 0**

## Red-team section

| Attack | Expected | Actual | Test | Correction |
|---|---|---|---|---|
| Future index / negative / slice / iteration | No future candles | Blocked | red-team / visible history | Visible end-exclusive view |
| Wrong TF / missing / extra / swapped context | ValidationError | Failed | bundle / red-team | Exact definition match |
| Forged bundle / envelope construction | ValidationError | Failed | red-team | Factory-only models |
| Provider one bar too early | Not called / not ready | Passed | feed readiness + golden A | Warmup + alignment |
| Exact-close withheld incorrectly | Ready at index 3 | Passed | golden A | Close-time mapping |
| Unsupported direction | Controlled failure | Failed closed | adapter test / golden D | Direction gate |
| List provider / raised provider | Sanitized execution error | Failed closed | provider tests | Existing engine boundary |
| Warmup zero, no closed context | Not ready | Passed | warmup-zero test | `max(1, warmup)` |
| Mutable list input | ValidationError | Failed | bundle tests | Tuple requirement |
| Context candle change | Bundle/envelope change | Passed | golden E / envelope sensitivity | Hash binding |

No remaining mandatory untested bypasses after the red-team loop.
