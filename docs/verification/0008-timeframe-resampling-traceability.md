# 0008 — Timeframe Resampling and Alignment Traceability

Milestone: **0.8 — Deterministic Candle Resampling and Multi-Timeframe Alignment**  
Base commit: `1ff0ea988a92b0c385912325d92b6b075b635e6b`

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

No remaining mandatory untested bypasses after the red-team loop.
