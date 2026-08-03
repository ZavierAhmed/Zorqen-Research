# 0007 — Strategy Definition Requirement Traceability

Milestone: **0.7 — Immutable Strategy Definition and Parameter Schema**  
Base commit: `b48ef6b9a7ef4c4325f34c5102dccf86c93e6f74`

Evidence classes: `PROVEN BY AUTOMATED TEST` · `VERIFIED BY SOURCE INSPECTION` · `NOT TESTED` · `NOT APPLICABLE`

## Acceptance matrix

| Requirement | Implementation | Automated test | Result |
|---|---|---|---|
| Immutable definition model | `domain/strategy_definitions/definitions.py` | `test_immutability` | PROVEN BY AUTOMATED TEST |
| Family ID/code exact pair | `strategy_families.require_seeded_family_pair` | `test_both_valid_seeded_pairs`, `test_correct_id_wrong_code`, `test_correct_code_wrong_id` | PROVEN BY AUTOMATED TEST |
| Unknown family ID/code fail | same | `test_unknown_id_and_code` | PROVEN BY AUTOMATED TEST |
| Nil UUID rejected | `identifiers.require_definition_uuid` | `test_definition_uuid_rejects_nil`, `test_nil_family_id_rejected_by_definition` | PROVEN BY AUTOMATED TEST |
| Strict MAJOR.MINOR.PATCH | `identifiers.require_semantic_version` | `test_valid_versions`, `test_invalid_versions` | PROVEN BY AUTOMATED TEST |
| Canonical lower_snake_case IDs | `identifiers.require_canonical_identifier` | `test_valid_identifiers`, `test_invalid_identifiers` | PROVEN BY AUTOMATED TEST |
| Draft may omit source hash | `StrategyDefinition.__post_init__` | `test_draft_without_source_hash` | PROVEN BY AUTOMATED TEST |
| Approved requires source hash | same | `test_approved_requires_valid_source_hash` | PROVEN BY AUTOMATED TEST |
| Approved hash lowercase hex only | `require_source_spec_sha256` | `test_source_hash_rules`, red-team hash prefix | PROVEN BY AUTOMATED TEST |
| Schema version only `"1"` | `StrategyDefinition` | `test_wrong_schema_version` | PROVEN BY AUTOMATED TEST |
| Decimal rejects float/bool/int/NaN | `DecimalParameterDefinition` | `test_decimal_rejects_float_bool_int_nan` | PROVEN BY AUTOMATED TEST |
| Decimal bounds/step alignment | same | `test_decimal_valid_and_alignment`, `test_decimal_minimum_relative_step` | PROVEN BY AUTOMATED TEST |
| Signed-zero canonical `"0"` | `format_canonical_decimal` | `test_signed_zero_canonical`, `test_no_runtime_metadata_and_decimal_zero` | PROVEN BY AUTOMATED TEST |
| Integer rejects bool/Decimal/float | `IntegerParameterDefinition` | `test_integer_rules` | PROVEN BY AUTOMATED TEST |
| Boolean rejects 0/1/strings | `BooleanParameterDefinition` | `test_boolean_rules` | PROVEN BY AUTOMATED TEST |
| Enum choices unique ordered tuple | `EnumParameterDefinition` | `test_enum_rules` | PROVEN BY AUTOMATED TEST |
| Duplicate/unsorted parameter keys fail | `require_canonical_parameters` | `test_duplicate_and_unsorted_parameter_keys` | PROVEN BY AUTOMATED TEST |
| Context TF unique / ordered / not execution | `require_canonical_context_requirements` | `test_context_timeframe_rules` | PROVEN BY AUTOMATED TEST |
| Warmup real int ≥0 bounded | definition/timeframes | `test_warmup_and_directions`, red-team bool warmup | PROVEN BY AUTOMATED TEST |
| Directions non-empty unique canonical | `require_canonical_directions` | `test_warmup_and_directions` | PROVEN BY AUTOMATED TEST |
| Binding missing/unknown/wrong kind fail | `bind_parameter_values` | `test_missing_unknown_wrong_kind_bounds` | PROVEN BY AUTOMATED TEST |
| Default binding helper | `bind_default_parameter_set` | `test_complete_valid_binding_and_defaults` | PROVEN BY AUTOMATED TEST |
| Definition/parameter/instance hashes stable | serialization | `test_repeated_serialization_identical`, `test_meaningful_changes_alter_hashes` | PROVEN BY AUTOMATED TEST |
| Input key order irrelevant | parsing+hash | `test_json_key_order_does_not_affect_hash` | PROVEN BY AUTOMATED TEST |
| No timestamps/paths/modules in bytes | serialization | `test_no_runtime_metadata_and_decimal_zero`, `test_no_dynamic_import_fields_in_schema` | PROVEN BY AUTOMATED TEST |
| Duplicate JSON keys rejected | `loads_strict_json` | `test_duplicate_keys_top_and_nested`, `test_parameter_values_duplicate_key_in_json` | PROVEN BY AUTOMATED TEST |
| BOM / invalid UTF-8 / trailing / array top | parsing | `test_bom_and_invalid_utf8`, `test_trailing_and_array_toplevel` | PROVEN BY AUTOMATED TEST |
| Unknown/missing fields / oversized / NaN | parsing | `test_unknown_and_missing_fields`, `test_oversized_input`, `test_json_nan_infinity` | PROVEN BY AUTOMATED TEST |
| Decimal JSON string canonical | parsing | `test_decimal_must_be_canonical_string` | PROVEN BY AUTOMATED TEST |
| NUL / long identifiers/descriptions | parsing+identifiers | `test_nul_and_long_text`, `test_display_text_rejects_nul_and_bounds` | PROVEN BY AUTOMATED TEST |
| Parser boundary sanitized | parsing | `test_parser_never_leaks_raw_exceptions` | PROVEN BY AUTOMATED TEST |
| CLI validate/bind success | `strategies/cli.py` | `test_validate_definition_success`, `test_bind_parameters_success` | PROVEN BY AUTOMATED TEST |
| CLI invalid/missing nonzero JSON stderr | CLI | `test_invalid_definition_exits_nonzero`, `test_missing_file_exits_nonzero` | PROVEN BY AUTOMATED TEST |
| No strategy logic / provider factory | package layout | Source inspection of `strategies/` + domain (no indicators) | VERIFIED BY SOURCE INSPECTION |
| No DB/API/migration for definitions | no new alembic/API | Source inspection; migration chain unchanged in verification | VERIFIED BY SOURCE INSPECTION |
| Approved ≠ executable | CLI flags + ADR | `executable_code_present` / `approved_means_executable` false in CLI tests | PROVEN BY AUTOMATED TEST |
| Test fixtures are draft-only | fixtures README + JSON | Fixture `status=draft`; `test_fixture_parses` | PROVEN BY AUTOMATED TEST |
| Reuse PositionDirection / Timeframe | imports | Source inspection + model tests | VERIFIED BY SOURCE INSPECTION |
| No third family | `SEEDED_FAMILY_PAIRS` | Source inspection of `strategy_families.py` | VERIFIED BY SOURCE INSPECTION |

**Summary:** mandatory automated rows proven; remaining rows are explicit source-inspection checks. **NOT TESTED: 0.**

## Red-team section

| Attack attempted | Expected failure | Actual result | Test | Correction |
|---|---|---|---|---|
| Mutable list choices/directions/context | ValidationError | Failed as expected | `test_mutable_containers_rejected` | None |
| Uppercase UUID string | Validation/ParseError | Failed as expected | `test_uppercase_uuid_and_hash_prefix_rejected` | None |
| `sha256:` hash prefix | ValidationError | Failed as expected | same | None |
| Bool warmup / float integer default | Validation/ParseError | Failed as expected | `test_bool_as_warmup_and_float_as_int` | None |
| Short-before-long / unsorted TF | ValidationError | Failed as expected | `test_short_before_long_and_unsorted_context` | None |
| Family ID/code mismatch via parser | ParseError | Failed as expected | `test_family_pair_enforced_in_parser` | None |
| Duplicate keys in parameter values JSON | ParseError | Failed as expected | `test_parameter_values_duplicate_key_in_json` | None |
| Infinite-style oversized document | ParseError size | Failed as expected | `test_oversized_input` | None |
| Non-canonical decimals `2.500`/`+2.5`/`02.5`/`-0` | ParseError | Failed as expected | `test_decimal_must_be_canonical_string` | None |
| Trailing second JSON object | ParseError | Failed (stdlib Extra data → sanitized) | `test_trailing_and_array_toplevel` | Test expectation adjusted to accept sanitized JSON error |
| Placeholder all-zero approved hash | ValidationError | Failed as expected | `test_approved_placeholder_and_draft_optional_hash` | None |

No remaining untested mandatory parser/constructor bypasses identified after the red-team loop.
