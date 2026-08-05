"""Unit tests for Adaptive MTF baseline contract integrity and resolution gates."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from zorqen_research.application.baselines.paths import family_baseline_dir, fixture_root
from zorqen_research.application.baselines.verification import (
    PINNED_MOMO_COMMIT,
    assert_no_strategy_provider_registered,
    validate_contract_document,
    validate_evidence_document,
    verify_baseline_family,
)
from zorqen_research.domain.artifacts import sha256_hex
from zorqen_research.domain.baselines.canonical import canonical_json_bytes, hash_canonical_document
from zorqen_research.domain.baselines.enums import ResolutionStatus
from zorqen_research.domain.baselines.errors import (
    BaselineValidationError,
    BaselineVerificationError,
)
from zorqen_research.domain.strategy_families import (
    ADAPTIVE_MTF_TREND_BREAKOUT_CODE,
    ADAPTIVE_MTF_TREND_BREAKOUT_ID,
)
from zorqen_research.strategies.cli import main


def _load_contract() -> dict[str, Any]:
    path = family_baseline_dir(ADAPTIVE_MTF_TREND_BREAKOUT_CODE) / "baseline_contract.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _load_evidence() -> dict[str, Any]:
    path = family_baseline_dir(ADAPTIVE_MTF_TREND_BREAKOUT_CODE) / "source_evidence.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_contract_schema_family_and_canonical_hash() -> None:
    contract = _load_contract()
    assert contract["schema_version"] == "1"
    assert contract["family_id"] == str(ADAPTIVE_MTF_TREND_BREAKOUT_ID)
    assert contract["family_code"] == ADAPTIVE_MTF_TREND_BREAKOUT_CODE
    assert contract["baseline_version"] == "1.0.0"
    assert contract["resolution_status"] == "RESOLVED"
    assert contract["unresolved_items"] == []
    path = family_baseline_dir(ADAPTIVE_MTF_TREND_BREAKOUT_CODE) / "baseline_contract.json"
    on_disk = path.read_bytes()
    assert on_disk == canonical_json_bytes(contract)
    digest = hash_canonical_document(contract, field="baseline_contract_hash")
    assert digest == sha256_hex(on_disk)
    assert digest == hash_canonical_document(contract, field="baseline_contract_hash")


def test_evidence_sorted_unique_claim_ids() -> None:
    evidence = _load_evidence()
    ids = [c["claim_id"] for c in evidence["claims"]]
    assert ids == sorted(ids)
    assert len(ids) == len(set(ids))


def test_duplicate_evidence_ids_rejected() -> None:
    contract = _load_contract()
    evidence = _load_evidence()
    evidence["claims"] = evidence["claims"] + [copy.deepcopy(evidence["claims"][0])]
    with pytest.raises(BaselineValidationError, match="duplicate"):
        validate_evidence_document(evidence, contract=contract, status=ResolutionStatus.RESOLVED)


def test_unknown_evidence_classification_rejected() -> None:
    contract = _load_contract()
    evidence = _load_evidence()
    evidence["claims"][0]["classification"] = "NOT_A_REAL_CLASS"
    with pytest.raises(BaselineValidationError, match="Unsupported evidence classification"):
        validate_evidence_document(evidence, contract=contract, status=ResolutionStatus.RESOLVED)


def test_missing_required_contract_fields_rejected() -> None:
    contract = _load_contract()
    del contract["protected_semantics"]
    with pytest.raises(BaselineValidationError, match="missing required fields"):
        validate_contract_document(contract)


def test_unsorted_evidence_rejected() -> None:
    contract = _load_contract()
    evidence = _load_evidence()
    evidence["claims"] = list(reversed(evidence["claims"]))
    with pytest.raises(BaselineValidationError, match="sorted"):
        validate_evidence_document(evidence, contract=contract, status=ResolutionStatus.RESOLVED)


def test_invalid_decimal_representation_rejected() -> None:
    contract = _load_contract()
    contract["volatility_rule"]["min_ratio"] = "1.00.0"
    with pytest.raises(BaselineValidationError, match="Decimal"):
        validate_contract_document(contract)


def test_local_path_leakage_rejected() -> None:
    contract = _load_contract()
    contract["authority"]["source_file_path"] = r"C:\Users\zasah\Documents\MomoQuant\file.cs"
    with pytest.raises(BaselineValidationError, match="absolute paths"):
        validate_contract_document(contract)


def test_resolved_with_unresolved_protected_field_fails() -> None:
    contract = _load_contract()
    contract["protected_semantics"]["entry"]["resolved"] = False
    with pytest.raises(BaselineVerificationError, match="unresolved protected"):
        validate_contract_document(contract)


def test_resolved_without_source_evidence_fails() -> None:
    contract = _load_contract()
    evidence = {"claims": []}
    with pytest.raises((BaselineValidationError, BaselineVerificationError)):
        validate_evidence_document(evidence, contract=contract, status=ResolutionStatus.RESOLVED)


def test_resolved_without_timing_executable_fails() -> None:
    contract = _load_contract()
    evidence = _load_evidence()
    for claim in evidence["claims"]:
        if (
            claim["claim_id"] in contract["protected_semantics"]["signal_timing"]["evidence_ids"]
            and claim["classification"] == "AUTHORITATIVE_EXECUTABLE"
        ):
            claim["classification"] = "AUTHORITATIVE_TEST"
    with pytest.raises(BaselineVerificationError, match="signal_timing"):
        validate_evidence_document(evidence, contract=contract, status=ResolutionStatus.RESOLVED)


def test_resolved_without_no_lookahead_executable_fails() -> None:
    contract = _load_contract()
    evidence = _load_evidence()
    for claim in evidence["claims"]:
        if (
            claim["claim_id"] in contract["protected_semantics"]["no_lookahead"]["evidence_ids"]
            and claim["classification"] == "AUTHORITATIVE_EXECUTABLE"
        ):
            claim["classification"] = "ILLUSTRATIVE_ONLY"
    with pytest.raises(BaselineVerificationError, match="no_lookahead"):
        validate_evidence_document(evidence, contract=contract, status=ResolutionStatus.RESOLVED)


def test_illustrative_only_cannot_satisfy_protected(
    tmp_path: Path,
) -> None:
    contract = _load_contract()
    evidence = _load_evidence()
    # Replace all entry evidence with illustrative-only.
    entry_ids = set(contract["protected_semantics"]["entry"]["evidence_ids"])
    for claim in evidence["claims"]:
        if claim["claim_id"] in entry_ids:
            claim["classification"] = "ILLUSTRATIVE_ONLY"
    with pytest.raises(BaselineVerificationError, match="entry"):
        validate_evidence_document(evidence, contract=contract, status=ResolutionStatus.RESOLVED)
    _ = tmp_path


def test_informational_default_alone_cannot_satisfy_warmup() -> None:
    contract = _load_contract()
    evidence = _load_evidence()
    warmup_ids = set(contract["protected_semantics"]["warmup"]["evidence_ids"])
    for claim in evidence["claims"]:
        if claim["claim_id"] in warmup_ids:
            claim["classification"] = "INFORMATIONAL_DEFAULT"
    with pytest.raises(BaselineVerificationError, match="warmup"):
        validate_evidence_document(evidence, contract=contract, status=ResolutionStatus.RESOLVED)


def test_approved_definition_bound_to_contract_hash() -> None:
    result = verify_baseline_family(ADAPTIVE_MTF_TREND_BREAKOUT_CODE)
    assert result.strategy_definition_hash is not None
    assert len(result.strategy_definition_hash) == 64
    definition_path = (
        family_baseline_dir(ADAPTIVE_MTF_TREND_BREAKOUT_CODE) / "approved_definition.json"
    )
    document = json.loads(definition_path.read_text(encoding="utf-8"))
    assert document["status"] == "approved"
    assert document["source_spec_sha256"] == result.baseline_contract_hash
    assert document["family_id"] == str(ADAPTIVE_MTF_TREND_BREAKOUT_ID)
    assert document["execution_timeframe"] == "5m"
    assert document["execution_warmup_bars"] == 165
    assert document["context_requirements"] == [{"timeframe": "1h", "warmup_bars": 205}]
    keys = [p["key"] for p in document["parameters"]]
    assert keys == sorted(keys)


def test_contract_change_changes_definition_binding() -> None:
    contract = _load_contract()
    original = hash_canonical_document(contract, field="baseline_contract_hash")
    contract["baseline_version"] = "1.0.1"
    altered = hash_canonical_document(contract, field="baseline_contract_hash")
    assert altered != original


def test_no_provider_registered() -> None:
    assert_no_strategy_provider_registered()


def test_fixture_manifest_and_candle_hashes() -> None:
    result = verify_baseline_family(ADAPTIVE_MTF_TREND_BREAKOUT_CODE)
    assert result.fixture_manifest_hash is not None
    root = fixture_root(ADAPTIVE_MTF_TREND_BREAKOUT_CODE)
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    for case in manifest["cases"]:
        assert case["provenance"]["commit_sha"] == PINNED_MOMO_COMMIT
        case_dir = root / case["case_id"]
        expected = json.loads((case_dir / "expected.json").read_text(encoding="utf-8"))
        assert expected["decision_close_time"].endswith("Z")
        assert expected["signal_emitted"] is True
        assert isinstance(expected["visible_context_count"], int)
        assert expected["visible_execution_count"] > expected["visible_context_count"]


def test_cli_verify_baseline_success(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["verify-baseline", "--family", ADAPTIVE_MTF_TREND_BREAKOUT_CODE])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["resolution_status"] == "RESOLVED"
    assert payload["provider_implementation_allowed"] is True
    assert payload["unresolved_count"] == 0
    assert payload["authority_commit"] == PINNED_MOMO_COMMIT
    assert len(payload["baseline_contract_hash"]) == 64
    assert len(payload["source_evidence_hash"]) == 64
    assert payload["fixture_manifest_hash"] is not None
    assert payload["strategy_definition_hash"] is not None


def test_cli_unknown_family(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["verify-baseline", "--family", "not_a_family"])
    assert code == 1
    err = json.loads(capsys.readouterr().err)
    assert err["ok"] is False
    assert "unknown" in err["error"].lower()


def test_cli_hash_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # Copy baselines into a temp repo-like layout and corrupt the contract bytes.
    from zorqen_research.application.baselines import paths as paths_mod

    src = family_baseline_dir(ADAPTIVE_MTF_TREND_BREAKOUT_CODE)
    fake_root = tmp_path / "repo"
    dest = fake_root / "baselines" / ADAPTIVE_MTF_TREND_BREAKOUT_CODE / "v1"
    dest.mkdir(parents=True)
    for name in (
        "baseline_contract.json",
        "source_evidence.json",
        "approved_definition.json",
    ):
        (dest / name).write_bytes((src / name).read_bytes())
    # Minimal pyproject marker for repository_root()
    (fake_root / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    (fake_root / "src" / "zorqen_research").mkdir(parents=True)
    # Corrupt contract while keeping valid JSON object shape that fails canonical check
    raw = json.loads((dest / "baseline_contract.json").read_text(encoding="utf-8"))
    (dest / "baseline_contract.json").write_text(json.dumps(raw, indent=2) + "\n", encoding="utf-8")
    fixtures_src = fixture_root(ADAPTIVE_MTF_TREND_BREAKOUT_CODE)
    fixtures_dest = fake_root / "tests" / "fixtures" / ADAPTIVE_MTF_TREND_BREAKOUT_CODE / "v1"
    fixtures_dest.mkdir(parents=True)

    def _copytree(src_dir: Path, dst_dir: Path) -> None:
        for path in src_dir.rglob("*"):
            rel = path.relative_to(src_dir)
            target = dst_dir / rel
            if path.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(path.read_bytes())

    _copytree(fixtures_src, fixtures_dest)

    monkeypatch.setattr(paths_mod, "repository_root", lambda: fake_root)
    code = main(["verify-baseline", "--family", ADAPTIVE_MTF_TREND_BREAKOUT_CODE])
    assert code == 1
    err = json.loads(capsys.readouterr().err)
    assert err["ok"] is False
    assert "canonical" in err["error"].lower()


def test_unresolved_cannot_ship_approved_definition(tmp_path: Path) -> None:
    contract = _load_contract()
    contract["resolution_status"] = "UNRESOLVED"
    contract["unresolved_items"] = ["example_gap"]
    contract["protected_semantics"]["entry"]["resolved"] = False
    # Direct gate: approved definition forbidden for non-RESOLVED
    from zorqen_research.application.baselines.verification import verify_approved_definition

    with pytest.raises(BaselineVerificationError, match="forbidden"):
        # Create a fake approved file
        baseline_dir = tmp_path / "v1"
        baseline_dir.mkdir()
        (baseline_dir / "approved_definition.json").write_text("{}", encoding="utf-8")
        verify_approved_definition(
            baseline_dir=baseline_dir,
            contract=contract,
            contract_hash="a" * 64,
            status=ResolutionStatus.UNRESOLVED,
        )


def test_contradictory_status_cannot_approve(tmp_path: Path) -> None:
    from zorqen_research.application.baselines.verification import verify_approved_definition

    baseline_dir = tmp_path / "v1"
    baseline_dir.mkdir()
    (baseline_dir / "approved_definition.json").write_text("{}", encoding="utf-8")
    with pytest.raises(BaselineVerificationError, match="forbidden"):
        verify_approved_definition(
            baseline_dir=baseline_dir,
            contract=_load_contract(),
            contract_hash="b" * 64,
            status=ResolutionStatus.CONTRADICTORY,
        )
