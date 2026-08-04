# 0008 — Timeframe Resampling and Alignment Traceability

Milestone: **0.8 / 0.8A — Deterministic Candle Resampling + Result Integrity Binding**  
Base commit (0.8A): `06951980cb1832c3c2a7e11d84675e741609c5b9`

Evidence classes: `PROVEN BY AUTOMATED TEST` · `VERIFIED BY SOURCE INSPECTION` · `NOT TESTED` · `NOT APPLICABLE`

## Acceptance matrix

| Requirement | Implementation | Automated test | Result |
|---|---|---|---|
| Exact integer derivation pairs | `derive_timeframe_plan` | `test_valid_derivation_pairs` | PROVEN BY AUTOMATED TEST |
| Reject non-integral / same / finer target | same | `test_invalid_derivation_pairs`, red-team | PROVEN BY AUTOMATED TEST |
| Reject wrong runtime types | same | `test_wrong_runtime_types` | PROVEN BY AUTOMATED TEST |
| Weekly max ratio 10080 | `MAX_DERIVATION_RATIO` | `test_valid_derivation_pairs` (1m→1w) | PROVEN BY AUTOMATED TEST |
| Source must be non-empty tuple of Candles | `resample_candles` | `test_empty_and_mutable_source_rejected` | PROVEN BY AUTOMATED TEST |
| Reject duplicate / gap / order / close-time | same | `test_non_candle_duplicate_gap_order`, `test_misaligned_open_and_invalid_close` | PROVEN BY AUTOMATED TEST |
| Reject forged source hash; input unchanged | same | `test_source_hash_mismatch_and_input_unchanged` | PROVEN BY AUTOMATED TEST |
| Leading/trailing partial buckets fail | same | `test_partial_buckets_and_missing_child` | PROVEN BY AUTOMATED TEST |
| Tuesday weekly start rejected | same | `test_partial_buckets_and_missing_child`, red-team | PROVEN BY AUTOMATED TEST |
| Exact OHLCV + large trade sum + signed zero | aggregation | `test_exact_aggregation_and_signed_zero_and_large_trades` | PROVEN BY AUTOMATED TEST |
| Deterministic hashes / sensitivity | series + CSV | `test_determinism_and_hash_sensitivity` | PROVEN BY AUTOMATED TEST |
| Context unavailable before close | `align_context_to_execution` | `test_availability_around_exact_close` | PROVEN BY AUTOMATED TEST |
| Exact-close available; 1ms early unavailable | `context_available_at_decision` | same | PROVEN BY AUTOMATED TEST |
| Same TF / finer / duplicate / unsorted fail | alignment | `test_symbol_same_tf_finer_duplicate_unsorted` | PROVEN BY AUTOMATED TEST |
| Mapping monotonic + linear pointer | `align_with_counting_context` | `test_mapping_monotonic_and_linear` | PROVEN BY AUTOMATED TEST |
| Alignment hash deterministic / sensitive | `MultiContextAlignment` | `test_alignment_hash_sensitivity` | PROVEN BY AUTOMATED TEST |
| Frozen resample + alignment goldens | `goldens.py` + CLI | `zorqen-timeframes verify-golden`, red-team CLI | PROVEN BY AUTOMATED TEST |
| Resampled source metadata cannot be forged | `ResampledCandleSeries.from_verified_series` | `test_forged_source_hash_direct_construction_rejected`, `test_forged_source_minimum_time_direct_construction_rejected`, `test_forged_source_maximum_time_direct_construction_rejected` | PROVEN BY AUTOMATED TEST |
| Source/target counts and bounds are computed | `from_verified_series` | `test_valid_normal_resampling_and_alignment_unchanged`, forged-bound tests | PROVEN BY AUTOMATED TEST |
| Canonical hashes cannot be caller supplied | public align/resample APIs | `test_public_alignment_rejects_caller_supplied_execution_hash`, `test_public_alignment_rejects_caller_supplied_context_hash`, `test_direct_unsafe_low_level_construction_unavailable` | PROVEN BY AUTOMATED TEST |
| Single alignment mapping length is exact | `_assert_mapping_bound_to_candles` | `test_mapping_shorter_than_execution_rejected`, `test_mapping_longer_than_execution_rejected` | PROVEN BY AUTOMATED TEST |
| Context indexes are in range | same | `test_context_index_equal_to_context_count_rejected`, `test_extremely_large_context_index_rejected` | PROVEN BY AUTOMATED TEST |
| Alignment mapping is recomputed from close times | `ContextAlignment.from_candles` | `test_monotonic_but_future_leaking_mapping_rejected`, `test_incorrect_null_before_already_closed_context_rejected`, `test_incorrect_context_index_when_newer_context_closed_rejected` | PROVEN BY AUTOMATED TEST |
| Single alignment hash is frozen | goldens + `alignment_hash` | `test_valid_normal_resampling_and_alignment_unchanged`, CLI golden | PROVEN BY AUTOMATED TEST |
| Multi alignment references exact child alignments | `MultiContextAlignment.from_alignments` | `test_valid_normal_resampling_and_alignment_unchanged`, `test_forged_multi_alignment_hash_direct_construction_rejected` | PROVEN BY AUTOMATED TEST |
| Unsafe low-level functions are not public | `domain.market_data.__all__` | `test_direct_unsafe_low_level_construction_unavailable` | PROVEN BY AUTOMATED TEST |
| Naive / non-zero-offset bounds rejected | factory-only construction | `test_naive_source_bound_direct_construction_rejected`, `test_nonzero_offset_source_bound_direct_construction_rejected` | PROVEN BY AUTOMATED TEST |
| Gapped / misaligned target factory rejected | `from_verified_series` | `test_gapped_target_candles_in_factory_rejected`, `test_misaligned_target_candle_in_factory_rejected` | PROVEN BY AUTOMATED TEST |
| No strategy/provider/backtest wiring | package layout | Source inspection | VERIFIED BY SOURCE INSPECTION |
| No new migration | alembic versions | Verification (0001–0003 only) | VERIFIED BY SOURCE INSPECTION |

**Summary: NOT TESTED: 0**

## Red-team section

| Attack | Expected | Actual | Test | Correction |
|---|---|---|---|---|
| `3m → 5m` | ValidationError | Failed | red-team / derivation | None |
| Same-timeframe derivation | ValidationError | Failed | same | None |
| Target finer than source | ValidationError | Failed | same | None |
| Partial first / final bucket | ValidationError | Failed | resampling / red-team | None |
| List instead of tuple | ValidationError | Failed | red-team | None |
| Forged source hash / all-zero | ValidationError | Failed | red-team | None |
| Tuesday weekly boundary | ValidationError | Failed | red-team | None |
| Mutation of result candles | TypeError | Failed | red-team | frozen tuple |
| Unsorted / duplicate contexts | AlignmentError | Failed | alignment / red-team | None |
| Symbol mismatch in multi | AlignmentError | Failed | alignment | None |
| Quadratic alignment probe | linear reads | Passed | counting sequence | monotonic pointer |
| Forged resampled source metadata | ResamplingValidationError | Failed | `test_timeframe_result_integrity` | factory-only series |
| Caller-supplied alignment hashes | AlignmentValidationError | Failed | integrity tests | hashes computed |
| Arbitrary mapping injection | AlignmentValidationError | Failed | `_assert_mapping_bound_to_candles` | recompute + bind |

No remaining mandatory untested bypasses after the red-team loop.

## Canonical contract note (0.8A)

Multi-context `alignment_hash` now includes ordered child `alignment_hashes` in addition to
candle hashes and mappings. The Milestone 0.8 value
`30abad8971a01b39c3a8579e9929c42f56fc168b4694885834ab911c9b1f904e` is replaced by the
independently derived
`1ced7609616bfc7e79039cd8ac9cbead378c7feffbeeec5db4bda3b7174f48ac`.

Single-context alignment hash (1h→4h golden):
`f8c8d2548fc6772ce421c9abb459efafd6e46aefd415dbf174406678f31d6698`.
