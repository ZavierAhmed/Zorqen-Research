# 0011 — Bounded Indicator Decision Feed Traceability

Milestone 1.1. Mandatory `NOT TESTED` count: **0**.

| Requirement | Implementation | Exact automated test | Evidence |
| ----------- | -------------- | -------------------- | -------- |
| Factory-bound `IndicatorSeriesKey` with exact code + canonical params | `domain/indicator_views/keys.py` | `test_canonical_series_ordering`, `test_redteam_mutated_hash_duplicate_bool_period_string_alias` | PROVEN BY AUTOMATED TEST |
| True Range key has empty parameters; others use `(("period", P),)` | `keys.py` `_canonicalize_key_parameters` | `test_require_lookup_and_missing`, `test_canonical_series_ordering` | PROVEN BY AUTOMATED TEST |
| EMA 20 vs 50 (period) keys distinct | `keys.py` `key_hash` | `test_all_indicator_view_golden_scenarios_pass` (`multiple-ema-keys`) | PROVEN BY AUTOMATED TEST |
| Duplicate keys rejected in bundle | `bundles.py` | `test_duplicate_key_rejected`, `test_redteam_mutated_hash_duplicate_bool_period_string_alias` | PROVEN BY AUTOMATED TEST |
| Direct forged key/bundle/view/history construction fails | `init=False` + raises | `test_direct_forged_bundle_construction_fails`, `test_direct_construction_blocked_and_safe_repr`, `test_direct_view_construction_blocked`, `test_redteam_bar_index_and_direct_history` | PROVEN BY AUTOMATED TEST |
| `IndicatorSeriesBundle.from_verified` exact input + exact series tuple | `bundles.py` | `test_exact_valid_bundle`, `test_mutable_series_list_rejected`, `test_tuple_subclass_rejected` | PROVEN BY AUTOMATED TEST |
| Empty series rejected | `bundles.py` | `test_empty_series_tuple_rejected` | PROVEN BY AUTOMATED TEST |
| Non-`IndicatorSeries` / forged `__new__` rejected | `bundles.py` | `test_non_indicator_series_item_rejected`, `test_redteam_tuple_subclass_and_forged_series` | PROVEN BY AUTOMATED TEST |
| Series must match symbol/timeframe/candle count/hash/math policy | `bundles.py` | `test_series_from_another_symbol_rejected`, `test_series_from_another_timeframe_rejected`, `test_series_from_another_candle_tuple_rejected`, `test_candle_count_mismatch_rejected` | PROVEN BY AUTOMATED TEST |
| Result hash reverified via canonical serialization | `bundles.py` + `hash_indicator_series` | `test_result_hash_mismatch_rejected`, `test_redteam_mutated_hash_duplicate_bool_period_string_alias` | PROVEN BY AUTOMATED TEST |
| Canonical series ordering by code then parameters | `bundles.py` | `test_canonical_series_ordering`, golden `multiple-ema-keys` | PROVEN BY AUTOMATED TEST |
| Bundle metadata + hash computed; caller cannot supply false counts/keys/hashes | `bundles.py` | `test_exact_valid_bundle`, `test_caller_cannot_supply_false_counts` | PROVEN BY AUTOMATED TEST |
| Internal `_VerifiedIndicatorSource` not exported | `domain/indicator_views/__init__.py` | `test_redteam_source_repr_slices_negative_future_sentinel` | PROVEN BY AUTOMATED TEST |
| Source safe repr/str (no values/length/result hash) | `histories.py` | `test_redteam_source_repr_slices_negative_future_sentinel` | PROVEN BY AUTOMATED TEST |
| Feed-owned binding verifies series identity from accepted bundle | `feed.py` | `test_feed_creation_scans_each_series_once_for_prefixes` | PROVEN BY AUTOMATED TEST |
| Prefix header excludes full input/result hashes and future counts | `prefix_hashes.py` + ADR 0011 | `test_cross_platform_canonical_header_bytes`, `test_redteam_signed_zero_and_view_hash_excludes_result_hash` | PROVEN BY AUTOMATED TEST |
| Prefix chain H0 / H(i+1) contract | `prefix_hashes.py` | `test_zero_and_one_value_prefix_and_undefined_token` | PROVEN BY AUTOMATED TEST |
| `None` → `null`; Decimal canonical UTF-8; signed zero → `"0"` | `canonical_value_token` | `test_zero_and_one_value_prefix_and_undefined_token`, `test_signed_zero_token_and_decimal_context_independence`, `test_redteam_signed_zero_and_view_hash_excludes_result_hash` | PROVEN BY AUTOMATED TEST |
| Prefix hashes O(n) once; `view_at` O(1) retrieve | `feed.py` / `histories.py` | `test_feed_creation_scans_each_series_once_for_prefixes`, `test_redteam_prefix_not_recomputed_and_large_index_constant` | PROVEN BY AUTOMATED TEST |
| Future mutation/append cannot alter earlier prefix/view hashes | feed + goldens | `test_future_mutation_and_append_independence`, `test_redteam_future_candle_mutation_append_and_decimal_context`, golden `future-independence` | PROVEN BY AUTOMATED TEST |
| Global Decimal context cannot alter prefix hashes | `prefix_hashes.py` | `test_signed_zero_token_and_decimal_context_independence`, `test_redteam_future_candle_mutation_append_and_decimal_context` | PROVEN BY AUTOMATED TEST |
| Visible value / metadata change alters hash | `prefix_hashes.py` | `test_visible_value_and_metadata_change_alter_hash` | PROVEN BY AUTOMATED TEST |
| Cross-platform canonical header bytes (no `\r`) | `prefix_hashes.py` | `test_cross_platform_canonical_header_bytes` | PROVEN BY AUTOMATED TEST |
| `VisibleIndicatorHistory` factory-controlled; no complete source API | `histories.py` | `test_iteration_and_no_complete_source_api`, `test_direct_construction_blocked_and_safe_repr`, golden `bounded-access` | PROVEN BY AUTOMATED TEST |
| Index/slice/iteration bounded to `end_exclusive` | `histories.py` | `test_index_equal_to_visible_count_and_oversized`, `test_bounded_slices_and_reverse`, `test_redteam_source_repr_slices_negative_future_sentinel` | PROVEN BY AUTOMATED TEST |
| Negative indexing stays inside visible prefix | `histories.py` | `test_negative_indexing_stays_visible`, `test_redteam_source_repr_slices_negative_future_sentinel` | PROVEN BY AUTOMATED TEST |
| `latest` / `latest_defined` / `defined_visible_count` O(1) | `histories.py` | `test_bar_zero_and_final_history`, `test_view_at_constant_value_reads_independent_of_bar_index` | PROVEN BY AUTOMATED TEST |
| Safe history representation | `histories.py` | `test_direct_construction_blocked_and_safe_repr`, golden `bounded-access` | PROVEN BY AUTOMATED TEST |
| No complete series in provider-visible views | `views.py` | `test_view_has_no_complete_series_or_bundle` | PROVEN BY AUTOMATED TEST |
| `IndicatorDecisionItem` ready = latest visible is Decimal | `views.py` | golden `warmup-progression`, `test_view_at_accepts_exact_indices` | PROVEN BY AUTOMATED TEST |
| No full input/candle/result hashes on items | `views.py` | `test_view_has_no_complete_series_or_bundle`, `test_redteam_signed_zero_and_view_hash_excludes_result_hash` | PROVEN BY AUTOMATED TEST |
| `IndicatorDecisionView` fields + overall_ready | `views.py` | `test_view_at_accepts_exact_indices`, golden `warmup-progression` | PROVEN BY AUTOMATED TEST |
| Decision-view hash excludes full result/input hashes | `views.py` `_from_feed` | `test_redteam_signed_zero_and_view_hash_excludes_result_hash`, `test_future_mutation_and_append_independence` | PROVEN BY AUTOMATED TEST |
| `view.require(IndicatorCode, period=...)` exact lookup | `views.py` | `test_require_lookup_and_missing` | PROVEN BY AUTOMATED TEST |
| String code / missing key / TR with period / period missing / bool period rejected | `views.py` / `keys.py` | `test_require_lookup_and_missing`, `test_redteam_mutated_hash_duplicate_bool_period_string_alias` | PROVEN BY AUTOMATED TEST |
| `IndicatorDecisionFeed.from_bundle` + `view_at` index validation | `feed.py` | `test_view_at_rejects_bool_float_negative_future`, `test_redteam_bar_index_and_direct_history` | PROVEN BY AUTOMATED TEST |
| No externally supplied `end_exclusive` / source / prefix hash on public API | feed/view construction | VERIFIED BY SOURCE INSPECTION of `feed.py` / `views.py` public methods; covered by direct-construction failures | VERIFIED BY SOURCE INSPECTION |
| View construction O(#indicators), independent of bar index | `feed.py` / `views.py` | `test_view_at_constant_value_reads_independent_of_bar_index` | PROVEN BY AUTOMATED TEST |
| No slicing / iteration / prefix rehash during `view_at` | feed + instrumented values | `test_view_at_constant_value_reads_independent_of_bar_index`, `test_redteam_prefix_not_recomputed_and_large_index_constant` | PROVEN BY AUTOMATED TEST |
| Bounded slicing costs only returned values | `histories.py` | `test_bounded_slice_costs_only_returned_values` | PROVEN BY AUTOMATED TEST |
| Future sentinel cannot leak via public access/repr | histories/views | `test_redteam_source_repr_slices_negative_future_sentinel`, golden `bounded-access` | PROVEN BY AUTOMATED TEST |
| No source length exposure | safe repr + no public len(source) | `test_direct_construction_blocked_and_safe_repr`, `test_redteam_source_repr_slices_negative_future_sentinel` | PROVEN BY AUTOMATED TEST |
| Literal feed/view goldens A–D | `application/indicator_views/goldens.py` | `test_all_indicator_view_golden_scenarios_pass`, CLI tests | PROVEN BY AUTOMATED TEST |
| `zorqen-indicators verify-view-golden` | `indicators/cli.py` | `test_indicator_view_cli_all_emits_json_and_exits_zero`, `test_indicator_view_cli_unknown_and_mismatch_nonzero`, `test_redteam_cli_all_failure_routing` | PROVEN BY AUTOMATED TEST |
| Existing `verify-golden` unchanged | `indicators/cli.py` + series goldens | `test_existing_verify_golden_unchanged` | PROVEN BY AUTOMATED TEST |
| Existing MTF provider types remain unchanged | no edits to MTF modules | `test_mtf_types_have_no_indicator_fields` | PROVEN BY AUTOMATED TEST |
| No strategy logic or provider integration | standalone feed only | `test_mtf_types_have_no_indicator_fields`; package layout under `indicator_views` | PROVEN BY AUTOMATED TEST |
| Prefix hashes depend only on visible values | chain definition | `test_future_mutation_and_append_independence`, golden `future-independence` | PROVEN BY AUTOMATED TEST |
| Constant-time view construction | instrumented structural tests | `test_view_at_constant_value_reads_independent_of_bar_index` | PROVEN BY AUTOMATED TEST |
| ADR 0011 documents prefix contract | `docs/adr/0011-no-lookahead-indicator-views.md` | document present; contract asserted in prefix tests | VERIFIED BY SOURCE INSPECTION |
| No FastAPI/SQLAlchemy/DB/artifact/Binance/backtest order deps in view layer | package imports | VERIFIED BY SOURCE INSPECTION of `domain/indicator_views` and `application/indicator_views` | VERIFIED BY SOURCE INSPECTION |
| No NumPy/pandas/TA libraries | package imports | VERIFIED BY SOURCE INSPECTION | VERIFIED BY SOURCE INSPECTION |
| No migration / API / frontend / persistence work | no new alembic/routes/UI | VERIFIED BY SOURCE INSPECTION; migrations remain `0001`–`0003` in verification evidence | VERIFIED BY SOURCE INSPECTION |
| Milestone 1.2 MTF composition not implemented | no MTF indicator wiring | `test_mtf_types_have_no_indicator_fields` | PROVEN BY AUTOMATED TEST |

## Totals

| Evidence class | Count |
| -------------- | ----- |
| PROVEN BY AUTOMATED TEST | 52 |
| VERIFIED BY SOURCE INSPECTION | 5 |
| NOT TESTED | **0** |
| NOT APPLICABLE | 0 |
