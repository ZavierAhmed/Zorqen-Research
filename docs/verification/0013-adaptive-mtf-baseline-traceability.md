# 0013 — Adaptive MTF Baseline Traceability

Milestone 1.3. Mandatory `NOT TESTED` count: **0**.

| Requirement | Implementation | Exact automated test | Evidence |
| --- | --- | --- | --- |
| Exact schema version | `baseline_contract.json` / `validate_contract_document` | `test_contract_schema_family_and_canonical_hash` | PROVEN BY AUTOMATED TEST |
| Exact family ID/code | contract + seeded families | `test_contract_schema_family_and_canonical_hash` | PROVEN BY AUTOMATED TEST |
| Stable baseline version | contract `baseline_version` | `test_contract_schema_family_and_canonical_hash` | PROVEN BY AUTOMATED TEST |
| Canonical JSON + deterministic hash | `canonical_json_bytes` / `hash_canonical_document` | `test_contract_schema_family_and_canonical_hash` | PROVEN BY AUTOMATED TEST |
| Duplicate evidence IDs rejected | `validate_evidence_document` | `test_duplicate_evidence_ids_rejected` | PROVEN BY AUTOMATED TEST |
| Unknown evidence classification rejected | `parse_evidence_classification` | `test_unknown_evidence_classification_rejected` | PROVEN BY AUTOMATED TEST |
| Missing required fields rejected | `validate_contract_document` | `test_missing_required_contract_fields_rejected` | PROVEN BY AUTOMATED TEST |
| Unsorted evidence arrays rejected | `validate_evidence_document` | `test_unsorted_evidence_rejected` | PROVEN BY AUTOMATED TEST |
| Invalid Decimal representation rejected | `_walk_reject_noncanonical_decimals` | `test_invalid_decimal_representation_rejected` | PROVEN BY AUTOMATED TEST |
| Local path leakage rejected | `reject_local_path_leakage` | `test_local_path_leakage_rejected`, `test_attack_local_absolute_paths` | PROVEN BY AUTOMATED TEST |
| RESOLVED with unresolved protected field fails | `validate_contract_document` | `test_resolved_with_unresolved_protected_field_fails` | PROVEN BY AUTOMATED TEST |
| RESOLVED without source evidence fails | `validate_evidence_document` | `test_resolved_without_source_evidence_fails` | PROVEN BY AUTOMATED TEST |
| RESOLVED without timing executable fails | protected gate | `test_resolved_without_timing_executable_fails` | PROVEN BY AUTOMATED TEST |
| RESOLVED without no-lookahead executable fails | protected gate | `test_resolved_without_no_lookahead_executable_fails` | PROVEN BY AUTOMATED TEST |
| Illustrative-only cannot satisfy claim | protected gate | `test_illustrative_only_cannot_satisfy_protected`, `test_attack_illustrative_json_as_authority` | PROVEN BY AUTOMATED TEST |
| Informational defaults cannot alone satisfy | protected gate | `test_informational_default_alone_cannot_satisfy_warmup`, `test_attack_frontend_label_as_executable` | PROVEN BY AUTOMATED TEST |
| UNRESOLVED/CONTRADICTORY cannot approve | `verify_approved_definition` | `test_unresolved_cannot_ship_approved_definition`, `test_contradictory_status_cannot_approve` | PROVEN BY AUTOMATED TEST |
| Approved definition family/timeframes/params | `verify_approved_definition` | `test_approved_definition_bound_to_contract_hash` | PROVEN BY AUTOMATED TEST |
| Contract hash bound via `source_spec_sha256` | approved definition | `test_approved_definition_bound_to_contract_hash` | PROVEN BY AUTOMATED TEST |
| Definition hash deterministic; contract change alters binding hash | hashing | `test_contract_change_changes_definition_binding`, `test_attack_alter_contract_after_hash` | PROVEN BY AUTOMATED TEST |
| No provider registered | `assert_no_strategy_provider_registered` | `test_no_provider_registered`, `test_attack_no_strategy_provider_and_no_momo_mutation` | PROVEN BY AUTOMATED TEST |
| Fixture manifests canonical; candle/expected hashes | `verify_fixture_manifest` | `test_fixture_manifest_and_candle_hashes` | PROVEN BY AUTOMATED TEST |
| Fixture provenance cites pinned MOMO commit | manifest provenance | `test_fixture_manifest_and_candle_hashes` | PROVEN BY AUTOMATED TEST |
| Decision-time safe expected traces | expected.json UTC Z | `test_fixture_manifest_and_candle_hashes` | PROVEN BY AUTOMATED TEST |
| CLI valid resolved output | `zorqen-strategy verify-baseline` | `test_cli_verify_baseline_success` | PROVEN BY AUTOMATED TEST |
| CLI unknown family / hash mismatch | CLI | `test_cli_unknown_family`, `test_cli_hash_mismatch` | PROVEN BY AUTOMATED TEST |
| Mixed MOMO commits rejected | evidence commit gate | `test_attack_mixed_momo_commits` | PROVEN BY AUTOMATED TEST |
| Invalid blob SHA rejected | `_require_git_blob_sha` | `test_attack_blob_hash_mismatch_shape` | PROVEN BY AUTOMATED TEST |
| Approve with unresolved items rejected | contract gate | `test_attack_approve_with_unresolved_items` | PROVEN BY AUTOMATED TEST |
| Altered expected trace detected via hash | fixture hashes | `test_attack_alter_parity_expected_trace` | PROVEN BY AUTOMATED TEST |
| atr_percentile marked NOT_IMPLEMENTED | contract comparison | `test_attack_atr_percentile_without_definition_marked_not_implemented` | PROVEN BY AUTOMATED TEST |
| No strategy execution / network / DB in CLI | `strategies/cli.py` | Source inspection + CLI tests | VERIFIED BY SOURCE INSPECTION |
| MOMO Quant unmodified | worktree detached HEAD | Source inspection of MOMO git status | VERIFIED BY SOURCE INSPECTION |
| Existing indicator/backtest hashes unchanged | goldens (verification suite) | Golden CLI runs in PROJECT_STATUS | VERIFIED BY SOURCE INSPECTION |

**Summary:** mandatory automated rows proven; remaining rows are explicit source-inspection checks. **NOT TESTED: 0.**

## Red-team section

| Attack | Expected failure | Actual result | Test | Correction |
| --- | --- | --- | --- | --- |
| Treat illustrative JSON as authoritative | VerificationError | Failed as expected | `test_attack_illustrative_json_as_authority` | None |
| Frontend/informational label as executable | VerificationError | Failed as expected | `test_attack_frontend_label_as_executable` | None |
| Mix MOMO commits | VerificationError | Failed as expected | `test_attack_mixed_momo_commits` | Pinned commit gate |
| Cite invalid blob hash | ValidationError | Failed as expected | `test_attack_blob_hash_mismatch_shape` | Git blob SHA-1 check |
| Resolve timing without bar-close evidence | VerificationError | Failed as expected | `test_attack_resolve_timing_without_bar_close_answer` | Executable timing gate |
| Resolve atr_percentile without definition | Documented NOT_IMPLEMENTED | Recorded | `test_attack_atr_percentile_without_definition_marked_not_implemented` | Comparison table |
| Approve with unresolved items | VerificationError | Failed as expected | `test_attack_approve_with_unresolved_items` | Empty unresolved gate |
| Alter contract after hash | Hash divergence | Detected | `test_attack_alter_contract_after_hash` | Canonical hash |
| Alter parity expected trace | Hash mismatch | Detected | `test_attack_alter_parity_expected_trace` | Fixture expected_hash |
| Include local absolute paths | ValidationError | Failed as expected | `test_attack_local_absolute_paths` | Path leakage scanner |
| Implement/register provider | VerificationError if present | Absent | `test_attack_no_strategy_provider_and_no_momo_mutation` | Explicit assert |
| Hide contradiction under RESOLVED | Counted; full verify rejects | Contradiction counted | `test_attack_hide_contradiction_as_resolved` | RESOLVED+contradiction gate in verify |
