"""Red-team attacks against Adaptive MTF baseline resolution."""

from __future__ import annotations

import copy
import json
from typing import Any

import pytest

from zorqen_research.application.baselines.paths import family_baseline_dir
from zorqen_research.application.baselines.verification import (
    PINNED_MOMO_COMMIT,
    assert_no_strategy_provider_registered,
    validate_contract_document,
    validate_evidence_document,
    verify_baseline_family,
)
from zorqen_research.domain.baselines.enums import ResolutionStatus
from zorqen_research.domain.baselines.errors import (
    BaselineValidationError,
    BaselineVerificationError,
)
from zorqen_research.domain.strategy_families import ADAPTIVE_MTF_TREND_BREAKOUT_CODE


def _contract() -> dict[str, Any]:
    path = family_baseline_dir(ADAPTIVE_MTF_TREND_BREAKOUT_CODE) / "baseline_contract.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _evidence() -> dict[str, Any]:
    path = family_baseline_dir(ADAPTIVE_MTF_TREND_BREAKOUT_CODE) / "source_evidence.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_attack_illustrative_json_as_authority() -> None:
    evidence = _evidence()
    contract = _contract()
    for claim in evidence["claims"]:
        claim["classification"] = "ILLUSTRATIVE_ONLY"
    with pytest.raises(BaselineVerificationError):
        validate_evidence_document(evidence, contract=contract, status=ResolutionStatus.RESOLVED)


def test_attack_frontend_label_as_executable() -> None:
    evidence = _evidence()
    contract = _contract()
    for claim in evidence["claims"]:
        if claim["claim_id"] in contract["protected_semantics"]["direction"]["evidence_ids"]:
            claim["classification"] = "INFORMATIONAL_DEFAULT"
            claim["notes"] = "Display name only"
    with pytest.raises(BaselineVerificationError, match="direction"):
        validate_evidence_document(evidence, contract=contract, status=ResolutionStatus.RESOLVED)


def test_attack_mixed_momo_commits() -> None:
    evidence = _evidence()
    contract = _contract()
    evidence["claims"][0]["commit_sha"] = "0" * 40
    with pytest.raises(BaselineVerificationError, match="pinned commit"):
        validate_evidence_document(evidence, contract=contract, status=ResolutionStatus.RESOLVED)


def test_attack_blob_hash_mismatch_shape() -> None:
    evidence = _evidence()
    contract = _contract()
    evidence["claims"][0]["blob_sha"] = "not-a-blob"
    with pytest.raises(BaselineValidationError, match="blob"):
        validate_evidence_document(evidence, contract=contract, status=ResolutionStatus.RESOLVED)


def test_attack_resolve_timing_without_bar_close_answer() -> None:
    contract = _contract()
    del contract["timing"]["decision_point"]
    # Still has required top-level timing object, but protected evidence gate is the binding.
    evidence = _evidence()
    for claim in evidence["claims"]:
        if claim["claim_id"] in contract["protected_semantics"]["signal_timing"]["evidence_ids"]:
            claim["classification"] = "MISSING"
    with pytest.raises(BaselineVerificationError, match="signal_timing"):
        validate_evidence_document(evidence, contract=contract, status=ResolutionStatus.RESOLVED)


def test_attack_atr_percentile_without_definition_marked_not_implemented() -> None:
    contract = _contract()
    assert (
        contract["master_spec_comparison"]["volatility.atr_percentile_55"]["result"]
        == "NOT_IMPLEMENTED"
    )
    assert contract["volatility_rule"]["atr_percentile"] == "NOT_IMPLEMENTED"


def test_attack_approve_with_unresolved_items() -> None:
    contract = _contract()
    contract["unresolved_items"] = ["gap"]
    with pytest.raises(BaselineVerificationError, match="empty unresolved"):
        validate_contract_document(contract)


def test_attack_alter_contract_after_hash() -> None:
    result = verify_baseline_family(ADAPTIVE_MTF_TREND_BREAKOUT_CODE)
    contract = _contract()
    contract["baseline_version"] = "9.9.9"
    from zorqen_research.domain.baselines.canonical import hash_canonical_document

    altered = hash_canonical_document(contract, field="baseline_contract_hash")
    assert altered != result.baseline_contract_hash


def test_attack_alter_parity_expected_trace() -> None:
    result = verify_baseline_family(ADAPTIVE_MTF_TREND_BREAKOUT_CODE)
    from zorqen_research.application.baselines.paths import fixture_root
    from zorqen_research.domain.artifacts import sha256_hex
    from zorqen_research.domain.baselines.canonical import canonical_json_bytes

    root = fixture_root(ADAPTIVE_MTF_TREND_BREAKOUT_CODE)
    expected_path = root / "long_entry" / "expected.json"
    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    expected["entry_price"] = "1"
    assert sha256_hex(canonical_json_bytes(expected)) != result.fixture_manifest_hash
    # Manifest expected_hash would mismatch if rewritten without updating manifest.
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    long_case = next(c for c in manifest["cases"] if c["case_id"] == "long_entry")
    assert long_case["expected_hash"] != sha256_hex(canonical_json_bytes(expected))


def test_attack_local_absolute_paths() -> None:
    contract = _contract()
    contract["source_files"][0]["path"] = "/Users/zasah/MomoQuant/evaluator.cs"
    with pytest.raises(BaselineValidationError, match="absolute"):
        validate_contract_document(contract)


def test_attack_no_strategy_provider_and_no_momo_mutation() -> None:
    assert_no_strategy_provider_registered()
    result = verify_baseline_family(ADAPTIVE_MTF_TREND_BREAKOUT_CODE)
    assert result.authority_commit == PINNED_MOMO_COMMIT
    assert result.provider_implementation_allowed is True


def test_attack_hide_contradiction_as_resolved() -> None:
    evidence = _evidence()
    contract = _contract()
    evidence["claims"] = copy.deepcopy(evidence["claims"])
    evidence["claims"][0]["classification"] = "CONTRADICTORY"
    # claim_ids must remain sorted
    evidence["claims"].sort(key=lambda c: c["claim_id"])
    # validate_evidence allows counting contradictions, but verify_baseline_family rejects RESOLVED
    unresolved, contradictions = validate_evidence_document(
        evidence, contract=contract, status=ResolutionStatus.RESOLVED
    )
    assert contradictions == 1
    assert unresolved == 0
