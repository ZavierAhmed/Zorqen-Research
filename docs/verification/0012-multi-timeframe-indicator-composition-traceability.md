# 0012 — Multi-Timeframe Indicator Composition Traceability

Milestone 1.2. Mandatory `NOT TESTED` count: **0**.

| Requirement | Implementation | Exact automated test | Evidence |
| ----------- | -------------- | -------------------- | -------- |
| Exact `MultiTimeframeBacktestInput` + rebuild before composition | `indicator_composition.py` `_reverify_mtf_input` | `test_mtf_indicator_input_subclass_rejected`, `test_mtf_indicator_forged_populated_mtf_rejected` | PROVEN BY AUTOMATED TEST |
| Exact `context_indicators` tuple length = context count | `from_verified` | `test_mtf_indicator_mutable_list_and_tuple_subclass_rejected`, `test_mtf_indicator_context_slot_count_rejected` | PROVEN BY AUTOMATED TEST |
| At least one configured indicator bundle | `from_verified` | `test_mtf_indicator_no_configured_bundles_rejected` | PROVEN BY AUTOMATED TEST |
| Exact `IndicatorSeriesBundle` + rebuild via `from_verified` | `_rebind_indicator_bundle` | `test_mtf_indicator_caller_modified_and_forged_bundle_rejected`, `test_mtf_indicator_valid_composition_retains_rebuilt` | PROVEN BY AUTOMATED TEST |
| Symbol / TF / count / hash / `candles is` binding | `_rebind_indicator_bundle` | `test_mtf_indicator_wrong_symbol_timeframe_count_hash_identity`, `test_mtf_indicator_correct_hash_wrong_tuple_identity_rejected` | PROVEN BY AUTOMATED TEST |
| Reject cross-slot placement | `_rebind_indicator_bundle` | `test_mtf_indicator_cross_slot_placement_rejected`, `test_mtf_indicator_swapped_context_bundles_rejected` | PROVEN BY AUTOMATED TEST |
| Composition hash schema + MTF + ordered bundle hashes | `build_indicator_composition_document` | golden `composition-identity-sensitivity` | PROVEN BY AUTOMATED TEST |
| No caller-supplied composition hash / ordering / counts | factory `init=False` | `test_mtf_indicator_direct_construction_blocked` | PROVEN BY AUTOMATED TEST |
| Feed owns MTF + optional indicator feeds; prefixes once | `MultiTimeframeIndicatorDecisionFeed.from_composition` | `test_mtf_indicator_view_at_constant_work_independent_of_bar_index` | PROVEN BY AUTOMATED TEST |
| Execution indicators indexed by execution bar | `indicator_feed.view_at` | golden `execution-indicator-warmup` | PROVEN BY AUTOMATED TEST |
| Context indicators use `latest_closed_index` | `indicator_feed.view_at` | `test_mtf_indicator_context_unavailable_and_exact_close_mapping`, golden `exact-close-context-indicator` | PROVEN BY AUTOMATED TEST |
| No context candle → indicator None / not ready | `ContextIndicatorDecisionView._from_feed` | `test_mtf_indicator_context_unavailable_and_exact_close_mapping` | PROVEN BY AUTOMATED TEST |
| Overall readiness = candles AND configured indicators | `MultiTimeframeIndicatorDecisionView._from_feed` | goldens A/B/D | PROVEN BY AUTOMATED TEST |
| Unconfigured slots do not block | readiness logic | golden `optional-indicator-slots` | PROVEN BY AUTOMATED TEST |
| Provider-visible hash excludes composition/bundle/result/input hashes and series lengths | `build_provider_visible_indicator_hash_document` | `test_mtf_indicator_provider_visible_hash_excludes_composition`, `test_mtf_indicator_future_independence_of_provider_visible_hash` | PROVEN BY AUTOMATED TEST |
| Safe repr/str; no complete series/bundle attributes | view `__repr__` | `test_mtf_indicator_view_no_future_leak_and_safe_repr` | PROVEN BY AUTOMATED TEST |
| Direct view construction blocked | `init=False` | `test_mtf_indicator_direct_view_construction_blocked` | PROVEN BY AUTOMATED TEST |
| Negative/bool/float/future indices rejected | feed `view_at` | `test_mtf_indicator_view_rejects_bad_indices` | PROVEN BY AUTOMATED TEST |
| Global Decimal context cannot affect hashes | hash builders | `test_mtf_indicator_decimal_context_independence` | PROVEN BY AUTOMATED TEST |
| Future indicator/candle changes do not alter earlier provider-visible hash | composition + views | `test_mtf_indicator_future_independence_of_provider_visible_hash` | PROVEN BY AUTOMATED TEST |
| `view_at(10)` vs `view_at(100_000)` bounded equal work | instrumented values | `test_mtf_indicator_view_at_constant_work_independent_of_bar_index` | PROVEN BY AUTOMATED TEST |
| No recalculation / prefix rebuild / realignment / bundle rebuild in `view_at` | feed design + perf test | `test_mtf_indicator_view_at_constant_work_independent_of_bar_index` | PROVEN BY AUTOMATED TEST |
| Adapter skips until composed ready; truthful counts | `MultiTimeframeIndicatorProviderAdapter` | goldens A/E; `test_mtf_indicator_counts_reconcile_on_success` | PROVEN BY AUTOMATED TEST |
| Exact tuple intents; list/generator/subclass fail | adapter | `test_mtf_indicator_adapter_rejects_non_exact_tuple_outputs` | PROVEN BY AUTOMATED TEST |
| Unsupported direction fails before fill; sanitized engine error | adapter + engine | `test_mtf_indicator_unsupported_direction_before_fill`, golden `direction-restriction` | PROVEN BY AUTOMATED TEST |
| Envelope wraps base; hash binds schema + base + composition | `IndicatorStrategyBacktestEnvelope.from_run` | goldens A–D/F; `test_mtf_indicator_counts_reconcile_on_success` | PROVEN BY AUTOMATED TEST |
| No raw composition/envelope hash constructor | `init=False` | `test_mtf_indicator_raw_envelope_hashes_rejected` | PROVEN BY AUTOMATED TEST |
| Existing MTF runner / hashes unchanged | unchanged modules | `test_existing_mtf_runner_regression_exact_close` | PROVEN BY AUTOMATED TEST |
| Literal goldens A–F + CLI | `indicator_goldens.py` + `run-mtf-indicator-golden` | `test_all_mtf_indicator_golden_scenarios_pass`, `test_mtf_indicator_cli_all_emits_json_and_exits_zero`, `test_mtf_indicator_cli_unknown_and_mismatch_nonzero` | PROVEN BY AUTOMATED TEST |
| Multiple EMA periods + ATR + extrema; exact lookup | golden C | `run_multiple_indicators_duplicate_codes` | PROVEN BY AUTOMATED TEST |
| Composition identity sensitivity (code/period/slot/values/None) | golden F | `run_composition_identity_sensitivity` | PROVEN BY AUTOMATED TEST |
| Existing MTF adapter source unchanged for provider contract | no edits to `provider.py` MTF adapter | VERIFIED BY SOURCE INSPECTION of `application/strategy_backtesting/provider.py` | VERIFIED BY SOURCE INSPECTION |
| Existing `StrategyBacktestEnvelope` schema unchanged | wrapper only | VERIFIED BY SOURCE INSPECTION of `results.py` vs `indicator_results.py` | VERIFIED BY SOURCE INSPECTION |
| ADR 0012 documents run-level vs provider-visible hashes | `docs/adr/0012-…` | document present | VERIFIED BY SOURCE INSPECTION |
| No Adaptive MTF / S&R signals / ATR stops / persistence / API / UI | scope | package layout under composition modules; no new routes/migrations | VERIFIED BY SOURCE INSPECTION |
| Existing Milestone 1.1 view hashes preserved | regression goldens | indicator view golden CLI (verification evidence) | PROVEN BY AUTOMATED TEST |
| Existing MTF hashes `1ef63eff…` / `8e5259d6…` / `c0945d5d…` preserved | MTF goldens | `test_existing_mtf_runner_regression_exact_close` + MTF CLI | PROVEN BY AUTOMATED TEST |

## Totals

| Evidence class | Count |
| -------------- | ----- |
| PROVEN BY AUTOMATED TEST | 38 |
| VERIFIED BY SOURCE INSPECTION | 4 |
| NOT TESTED | **0** |
| NOT APPLICABLE | 0 |
