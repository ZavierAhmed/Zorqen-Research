# 0010 — Deterministic Indicator Series Foundation Traceability

Milestone: **1.0 — Deterministic Indicator Series Foundation**  
Base commit: `9b5f030c1209f435b481f60ed8571128f11a50be`

Evidence classes: `PROVEN BY AUTOMATED TEST` · `VERIFIED BY SOURCE INSPECTION` · `NOT TESTED` · `NOT APPLICABLE`

## Acceptance matrix

| Requirement | Implementation | Exact automated test | Evidence |
|---|---|---|---|
| Factory-bound IndicatorInput | `IndicatorInput.from_verified` | `test_indicator_input_accepts_exact_valid_tuple`, `test_indicator_input_rejects_direct_forged_construction` | PROVEN BY AUTOMATED TEST |
| Reject empty / list / non-candle / duplicate / OOO / gap / misaligned | input factory + `require_canonical_series` | `test_indicator_input_rejects_empty_tuple`, `test_indicator_input_rejects_mutable_list`, `test_indicator_input_rejects_non_candle_item`, `test_indicator_input_rejects_duplicate_candle`, `test_indicator_input_rejects_out_of_order_candle`, `test_indicator_input_rejects_gap`, `test_indicator_input_rejects_misaligned_candle` | PROVEN BY AUTOMATED TEST |
| Reject invalid symbol/timeframe types | input factory | `test_indicator_input_rejects_invalid_symbol_type`, `test_indicator_input_rejects_invalid_timeframe_type` | PROVEN BY AUTOMATED TEST |
| Computed candle hash and bounds | input factory | `test_indicator_input_computed_hash_and_bounds` | PROVEN BY AUTOMATED TEST |
| Fixed math policy schema/precision/rounding | `default_math_policy` | `test_math_policy_rejects_direct_construction`, goldens `decimal-context` | PROVEN BY AUTOMATED TEST |
| Local Decimal context independence | calculators + `localcontext` | `test_ema_global_decimal_context_independence`, `test_true_range_atr_global_context_independence`, `test_redteam_global_decimal_precision_extremely_low`, CLI `decimal-context` | PROVEN BY AUTOMATED TEST |
| Period validation 1..1e6; reject bool/float/Decimal/str/0/neg/max+1 | `require_period` | `test_require_period_accepts_valid_ints`, `test_require_period_rejects_invalid`, `test_ema_rejects_bool_period`, `test_redteam_period_true_and_over_maximum` | PROVEN BY AUTOMATED TEST |
| Period > length → all undefined | EMA path | `test_period_greater_than_input_length_yields_all_undefined` | PROVEN BY AUTOMATED TEST |
| Factory-bound IndicatorSeries; forged construction fails | `IndicatorSeries.from_calculation` | `test_series_rejects_direct_forged_construction`, `test_redteam_forged_input_and_result_hashes` | PROVEN BY AUTOMATED TEST |
| Values length / float / int / bool / NaN / Inf rejected | result validation | `test_series_rejects_values_length_mismatch`, `test_series_rejects_float_int_bool_values`, `test_series_rejects_nan_and_infinity`, `test_redteam_float_and_non_finite_smuggled_into_result`, `test_redteam_result_value_length_mismatch` | PROVEN BY AUTOMATED TEST |
| Signed zero canonical `"0"` | result + serialization | `test_signed_zero_serializes_as_zero`, `test_redteam_signed_zero_canonical` | PROVEN BY AUTOMATED TEST |
| Canonical JSON + SHA-256 (no result hash in payload) | `serialize_indicator_series_bytes` / `hash_indicator_series_payload` | `test_deterministic_canonical_bytes_and_hash_sensitivity` | PROVEN BY AUTOMATED TEST |
| Stable IndicatorCode values only | `IndicatorCode` StrEnum | `test_unknown_indicator_code_type_rejected`, `test_redteam_unknown_indicator_code_rejected` | PROVEN BY AUTOMATED TEST |
| EMA period 1 / seed / recurrence / warmup | `ema_close` | `test_ema_period_one_equals_close`, `test_ema_exact_seed_and_recurrence`, `test_ema_warmup_none_before_seed` | PROVEN BY AUTOMATED TEST |
| EMA prefix equivalence / future independence | `ema_close` | `test_ema_prefix_equivalence`, `test_ema_future_candle_independence`, `test_redteam_future_candle_changed_and_appended` | PROVEN BY AUTOMATED TEST |
| EMA large/small finite prices | `ema_close` | `test_ema_large_and_small_finite_prices`, `test_redteam_very_large_and_small_magnitudes` | PROVEN BY AUTOMATED TEST |
| True Range first / up gap / down gap / non-negative | `true_range` | `test_true_range_first_candle_and_gaps` | PROVEN BY AUTOMATED TEST |
| Wilder ATR period 1 / seed / recurrence / warmup | `wilder_atr` | `test_wilder_atr_period_one_equals_tr`, `test_wilder_atr_seed_recurrence_warmup` | PROVEN BY AUTOMATED TEST |
| TR/ATR prefix equivalence | volatility | `test_true_range_and_atr_prefix_equivalence` | PROVEN BY AUTOMATED TEST |
| Inclusive rolling extrema / duplicates / inc/dec | `rolling_highest` / `rolling_lowest` | `test_rolling_period_one_equals_current`, `test_rolling_warmup_and_duplicates`, `test_rolling_strictly_increasing_and_decreasing` | PROVEN BY AUTOMATED TEST |
| Prior-window excludes current | `prior_rolling_*` | `test_prior_period_one_equals_previous`, `test_prior_excludes_current_candle`, `test_current_candle_mutation_does_not_affect_prior_at_same_index`, `test_redteam_current_candle_change_prior_only`, `test_redteam_duplicate_rolling_highs_lows` | PROVEN BY AUTOMATED TEST |
| Extrema prefix equivalence | extrema | `test_extrema_prefix_equivalence` | PROVEN BY AUTOMATED TEST |
| O(n) rolling / prior (instrumented reads) | monotonic deque + `CountingSequence` | `test_rolling_linear_operation_bound`, `test_prior_linear_operation_bound`, `test_redteam_rolling_not_quadratic` | PROVEN BY AUTOMATED TEST |
| Literal goldens + CLI | `goldens.py` + `zorqen-indicators` | `test_all_indicator_golden_scenarios_pass`, `test_indicator_cli_all_emits_json_and_exits_zero`, `test_indicator_cli_unknown_scenario_nonzero`, `test_redteam_cli_unknown_scenario_and_mismatch` | PROVEN BY AUTOMATED TEST |
| No IndicatorSeries on decision feed / contexts / history | package boundary | `test_redteam_indicator_series_not_in_decision_feed_types` | PROVEN BY AUTOMATED TEST |
| No provider-safe bounded views / persistence / API | absence | Source inspection of routes/migrations/provider packages | VERIFIED BY SOURCE INSPECTION |
| No strategy signals / Adaptive MTF / S&R rules | absence | Source inspection | VERIFIED BY SOURCE INSPECTION |
| No NumPy/pandas/TA-Lib | pyproject + imports | Source inspection | VERIFIED BY SOURCE INSPECTION |
| Migration chain remains 0001–0003 | alembic | Verification commands | VERIFIED BY SOURCE INSPECTION |
| Existing frozen hashes unchanged | regression CLIs | `zorqen-backtest` / `zorqen-timeframes` / MTF goldens | PROVEN BY AUTOMATED TEST |

**Summary: NOT TESTED: 0**

## Red-team section

| # | Attack | Expected | Actual | Test | Correction |
|---|---|---|---|---|---|
| 1 | Global Decimal precision extremely low | Unchanged outputs/hashes | Passed | `test_redteam_global_decimal_precision_extremely_low` | Local context |
| 2 | Global rounding changed | Unchanged | Passed | same + ATR/EMA context tests | Local context |
| 3 | Period `True` | Rejected | Failed closed | `test_redteam_period_true_and_over_maximum` | `type is int` |
| 4 | Period > maximum | Rejected | Failed closed | same | Upper bound |
| 5 | Float smuggled into result | Rejected | Failed closed | `test_redteam_float_and_non_finite_smuggled_into_result` | Strict Decimal check |
| 6 | Non-finite Decimal | Rejected | Failed closed | same | `is_finite` |
| 7 | Signed zero | Canonical `"0"` | Passed | `test_redteam_signed_zero_canonical` | Normalize `== 0` |
| 8 | Future candle changed | Prefix unchanged | Passed | `test_redteam_future_candle_changed_and_appended` | Causal recurrence |
| 9 | Future candle appended | Prefix unchanged | Passed | same | Causal recurrence |
| 10 | Current candle changed (prior extrema) | Prior level unchanged at index | Passed | `test_redteam_current_candle_change_prior_only` | Exclude current |
| 11 | Duplicate rolling highs/lows | Deterministic extreme | Passed | `test_redteam_duplicate_rolling_highs_lows` | Monotonic deque `<=`/`>=` |
| 12 | Very large Decimal magnitude | Finite defined values | Passed | `test_redteam_very_large_and_small_magnitudes` | Prec 50 local |
| 13 | Very small Decimal magnitude | Finite defined values | Passed | same | Prec 50 local |
| 14 | Direct forged input hash | Construction rejected | Failed closed | `test_redteam_forged_input_and_result_hashes` | Factory-only |
| 15 | Direct forged result hash | Construction rejected | Failed closed | same | Factory-only |
| 16 | Result value length mismatch | Rejected | Failed closed | `test_redteam_result_value_length_mismatch` | Length check |
| 17 | Force quadratic rolling | Read bound ≪ n·period | Passed | `test_redteam_rolling_not_quadratic` | Monotonic deque |
| 18 | Pass IndicatorSeries into decision feed | No field / annotation | Passed | `test_redteam_indicator_series_not_in_decision_feed_types` | No integration |
| 19 | Unknown indicator code | Rejected | Failed closed | `test_redteam_unknown_indicator_code_rejected` | Closed StrEnum |
| 20 | CLI mismatch / unknown scenario | Nonzero exit + JSON error | Passed | `test_redteam_cli_unknown_scenario_and_mismatch` | CLI checks |

No remaining mandatory untested bypasses after the red-team loop.
