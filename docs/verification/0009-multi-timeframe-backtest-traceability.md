# 0009 — Multi-Timeframe Backtest Decision Feed Traceability

Milestone: **0.9 / 0.9A / 0.9B — Deterministic Multi-Timeframe Backtest Decision Feed**  
Base commit (0.9): `3ac02582af357cf91a3080149abf470d2f60222c`  
Corrective base (0.9A): `b8080301a5f70d8a3ed42203479a4927778eb826`  
Corrective base (0.9B): `28de6a0c22b8572a05f5a627b1c9b541632eec6a`

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
| Envelope binds identities; forged construction fails | `StrategyBacktestEnvelope.from_run` | `test_envelope_*`, `test_envelope_rejects_raw_hash_factory_and_direct_construction` | PROVEN BY AUTOMATED TEST |
| Envelope identity cannot be caller supplied | `from_run` derives hashes from bundle/policy/result | `test_envelope_rejects_raw_hash_factory_and_direct_construction`, `test_envelope_cannot_forge_identity_hashes_or_mismatched_result` | PROVEN BY AUTOMATED TEST |
| Envelope count reconciliation | invocation + warmup skip == execution count | `test_envelope_count_reconciliation_and_types` | PROVEN BY AUTOMATED TEST |
| Adapter identities come only from the feed | `MultiTimeframeProviderAdapter(feed, provider)` | `test_adapter_identities_only_from_feed_and_base_checks` | PROVEN BY AUTOMATED TEST |
| Decision-view hashes come only from the bundle | feed-owned `_from_feed` builders | `test_views_reject_caller_supplied_hashes_and_forged_factories` | PROVEN BY AUTOMATED TEST |
| History views perform no prefix slicing | `VisibleCandleHistory._from_verified_source` | `test_visible_history_constant_time_construction` | PROVEN BY AUTOMATED TEST |
| Per-bar construction is constant-time | feed `view_at` + internal source | `test_visible_history_constant_time_construction` | PROVEN BY AUTOMATED TEST |
| Tuple subclasses are rejected | adapter `type(intents) is tuple` | `test_provider_exact_tuple_contract` | PROVEN BY AUTOMATED TEST |
| Direction golden verifies the exact cause | `run_direction_restriction` | `test_direction_golden_exact_cause_and_truthful_invocation_count` | PROVEN BY AUTOMATED TEST |
| Direction golden reports truthful provider invocation count | CLI payload `provider_invocation_count: 1` | `test_direction_golden_exact_cause_and_truthful_invocation_count`, MTF golden D | PROVEN BY AUTOMATED TEST |
| Complete source is not publicly exposed | no `source_object` / `candles` / conversion APIs | `test_provider_cannot_obtain_future_candles_through_public_apis`, `test_trusted_source_is_internal_only` | PROVEN BY AUTOMATED TEST |
| Execution history cannot reveal future candles | bounded index/slice/iter | `test_provider_cannot_obtain_future_candles_through_public_apis`, no-lookahead probe | PROVEN BY AUTOMATED TEST |
| Context history cannot reveal future candles | bounded index/slice/iter | `test_provider_cannot_obtain_future_candles_through_public_apis`, no-lookahead probe | PROVEN BY AUTOMATED TEST |
| Trusted unchecked construction is internal only | `_VerifiedHistorySource._bind_trusted` | `test_trusted_source_is_internal_only` | PROVEN BY AUTOMATED TEST |
| Context view history is bound to its `ContextSeriesInput` | `_from_feed` identity check | `test_view_content_bound_to_exact_feed_sources` | PROVEN BY AUTOMATED TEST |
| Execution history is bound to the input bundle | `_from_feed` identity check | `test_view_content_bound_to_exact_feed_sources` | PROVEN BY AUTOMATED TEST |
| Performance proof uses no public source-exposure API | private `_source` inspection | `test_visible_history_constant_time_construction` | PROVEN BY AUTOMATED TEST |
| Frozen MTF goldens A–E + no-lookahead probe | `goldens.py` + CLI | `zorqen-backtest run-mtf-golden`, `test_no_lookahead_probe_golden_preserves_exact_close_hashes` | PROVEN BY AUTOMATED TEST |
| Existing seven result hashes unchanged | `BacktestEngine` untouched | `zorqen-backtest run-golden` | PROVEN BY AUTOMATED TEST |
| Existing alignment/resample hashes unchanged | no 0.8A contract change | `zorqen-timeframes verify-golden` | PROVEN BY AUTOMATED TEST |
| No strategy algorithms / persistence / API | package layout | Source inspection | VERIFIED BY SOURCE INSPECTION |
| No new migration | alembic versions | Verification (0001–0003 only) | VERIFIED BY SOURCE INSPECTION |

**Summary: NOT TESTED: 0**

## Red-team section

| Attack | Expected | Actual | Test | Correction |
|---|---|---|---|---|
| Future index / negative / slice / iteration | No future candles | Blocked | red-team / visible history / 0.9B probe | Visible end-exclusive view |
| Public full-source accessors | Absent | Blocked | 0.9B no-lookahead tests | Removed `source_object` / public trusted API |
| Inject foreign history into decision view | Impossible / ValidationError | Failed | `test_view_content_bound_to_exact_feed_sources` | Feed-owned `_from_feed` only |
| Wrong TF / missing / extra / swapped context | ValidationError | Failed | bundle / red-team | Exact definition match |
| Forged bundle / envelope construction | ValidationError | Failed | red-team / 0.9A envelope tests | Factory-only models |
| Caller-supplied envelope / view hashes | Rejected | Failed | 0.9A identity binding tests | `from_run` / bundle-derived views |
| Provider one bar too early | Not called / not ready | Passed | feed readiness + golden A | Warmup + alignment |
| Exact-close withheld incorrectly | Ready at index 3 | Passed | golden A | Close-time mapping |
| Unsupported direction | Exact cause + 1 invocation | Failed closed | direction golden / 0.9A test | Direction gate + truthful counts |
| List / generator / tuple subclass provider | Sanitized execution error | Failed closed | `test_provider_exact_tuple_contract` | Exact `type is tuple` |
| Multi-intent provider | Engine validation error | Failed closed | `test_provider_exact_tuple_contract` | Existing one-intent limit |
| Warmup zero, no closed context | Not ready | Passed | warmup-zero test | `max(1, warmup)` |
| Mutable list input | ValidationError | Failed | bundle tests | Tuple requirement |
| Context candle change | Bundle/envelope change | Passed | golden E / envelope sensitivity | Hash binding |
| O(n) prefix copy per bar | Constant-time view construction | Passed | instrumented history test | Internal source + end_exclusive |

No remaining mandatory untested bypasses after the red-team loop.
