"""Verification gates for Adaptive MTF baseline contracts and evidence."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from zorqen_research.application.baselines.loading import load_json_object
from zorqen_research.application.baselines.paths import (
    ADAPTIVE_MTF_FAMILY_CODE,
    CONTRACT_FILENAME,
    DEFINITION_FILENAME,
    EVIDENCE_FILENAME,
    SUPPORTED_FAMILIES,
    family_baseline_dir,
    fixture_root,
)
from zorqen_research.application.strategy_definitions.parsing import parse_definition_file
from zorqen_research.application.strategy_definitions.serialization import hash_definition
from zorqen_research.domain.artifacts import sha256_hex
from zorqen_research.domain.baselines.canonical import (
    canonical_json_bytes,
    hash_canonical_document,
    reject_local_path_leakage,
)
from zorqen_research.domain.baselines.enums import (
    AUTHORITATIVE_EVIDENCE,
    NON_AUTHORITATIVE_EVIDENCE,
    PROTECTED_SEMANTIC_KEYS,
    EvidenceClassification,
    ResolutionStatus,
    parse_evidence_classification,
    parse_resolution_status,
)
from zorqen_research.domain.baselines.errors import (
    BaselineValidationError,
    BaselineVerificationError,
)
from zorqen_research.domain.strategy_definitions.enums import DefinitionStatus
from zorqen_research.domain.strategy_families import (
    ADAPTIVE_MTF_TREND_BREAKOUT_CODE,
    ADAPTIVE_MTF_TREND_BREAKOUT_ID,
)

CONTRACT_SCHEMA_VERSION = "1"
REQUIRED_CONTRACT_FIELDS: frozenset[str] = frozenset(
    {
        "schema_version",
        "resolution_status",
        "family_id",
        "family_code",
        "baseline_code",
        "baseline_version",
        "authority",
        "source_files",
        "source_tests",
        "identity",
        "timeframes",
        "indicator_requirements",
        "parameters",
        "trend_rule",
        "breakout_rule",
        "retest_rule",
        "volatility_rule",
        "stop_rule",
        "target_rule",
        "timing",
        "state_machine",
        "outputs",
        "protected_semantics",
        "master_spec_comparison",
        "unresolved_items",
    }
)

REQUIRED_EVIDENCE_FIELDS: frozenset[str] = frozenset(
    {
        "claim_id",
        "claim",
        "classification",
        "repository",
        "commit_sha",
        "file_path",
        "blob_sha",
        "symbol",
        "line_or_member_reference",
        "supporting_test",
        "notes",
    }
)

REQUIRED_AUTHORITY_FIELDS: frozenset[str] = frozenset(
    {
        "repository",
        "commit_sha",
        "inspection_date",
        "source_file_path",
        "source_blob_sha",
        "source_symbol_or_type",
        "evidence_class",
    }
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_GIT_BLOB_RE = re.compile(r"^[0-9a-f]{40}$")
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
_DECIMAL_RE = re.compile(r"^-?(?:0|[1-9]\d*)(?:\.\d+)?$")

PINNED_MOMO_COMMIT = "766e31db73bbb130d12ba84f1568745210db6155"
PINNED_MOMO_REPOSITORY = "ZavierAhmed/MomoQuant"


@dataclass(frozen=True, slots=True)
class BaselineVerificationResult:
    ok: bool
    family_code: str
    resolution_status: str
    authority_repository: str
    authority_commit: str
    baseline_version: str
    baseline_contract_hash: str
    source_evidence_hash: str
    fixture_manifest_hash: str | None
    strategy_definition_hash: str | None
    unresolved_count: int
    contradiction_count: int
    provider_implementation_allowed: bool

    def to_document(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "family_code": self.family_code,
            "resolution_status": self.resolution_status,
            "authority_repository": self.authority_repository,
            "authority_commit": self.authority_commit,
            "baseline_version": self.baseline_version,
            "baseline_contract_hash": self.baseline_contract_hash,
            "source_evidence_hash": self.source_evidence_hash,
            "fixture_manifest_hash": self.fixture_manifest_hash,
            "strategy_definition_hash": self.strategy_definition_hash,
            "unresolved_count": self.unresolved_count,
            "contradiction_count": self.contradiction_count,
            "provider_implementation_allowed": self.provider_implementation_allowed,
        }


def _require_object(value: object, *, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        msg = f"{field} must be a JSON object"
        raise BaselineValidationError(msg)
    return value


def _require_list(value: object, *, field: str) -> list[Any]:
    if not isinstance(value, list):
        msg = f"{field} must be a JSON array"
        raise BaselineValidationError(msg)
    return value


def _require_string(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        msg = f"{field} must be a non-empty trimmed string"
        raise BaselineValidationError(msg)
    return value


def _require_sha256(value: object, *, field: str) -> str:
    text = _require_string(value, field=field)
    if not _SHA256_RE.fullmatch(text):
        msg = f"{field} must be exactly 64 lowercase hexadecimal characters"
        raise BaselineValidationError(msg)
    return text


def _require_git_blob_sha(value: object, *, field: str) -> str:
    """Git object IDs at the pinned MOMO commit are SHA-1 (40 hex chars)."""
    text = _require_string(value, field=field)
    if not _GIT_BLOB_RE.fullmatch(text):
        msg = f"{field} must be a 40-character lowercase git blob SHA"
        raise BaselineValidationError(msg)
    return text


def _require_commit(value: object, *, field: str) -> str:
    text = _require_string(value, field=field)
    if not _COMMIT_RE.fullmatch(text):
        msg = f"{field} must be a 40-character lowercase commit SHA"
        raise BaselineValidationError(msg)
    return text


def _walk_reject_noncanonical_decimals(node: object, *, field: str) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            _walk_reject_noncanonical_decimals(value, field=f"{field}.{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            _walk_reject_noncanonical_decimals(value, field=f"{field}[{index}]")
    elif isinstance(node, float):
        msg = f"{field} must not use JSON number floats; use canonical decimal strings"
        raise BaselineValidationError(msg)
    elif isinstance(node, str) and _looks_like_decimal_field(field):
        if not _DECIMAL_RE.fullmatch(node):
            msg = f"{field} has invalid Decimal representation: {node!r}"
            raise BaselineValidationError(msg)
        if node.startswith("+") or (node.startswith("0") and len(node) > 1 and node[1] != "."):
            msg = f"{field} must be a canonical Decimal string: {node!r}"
            raise BaselineValidationError(msg)
        # Reject trailing bare "." while allowing fixed-scale forms like "1.00".
        if node.endswith("."):
            msg = f"{field} must be a canonical Decimal string: {node!r}"
            raise BaselineValidationError(msg)


def _looks_like_decimal_field(field: str) -> bool:
    leaf = field.rsplit(".", maxsplit=1)[-1].lower()
    exact = {
        "default",
        "default_value",
        "minimum",
        "maximum",
        "step",
        "min_ratio",
        "max_ratio",
        "tolerance_atr",
        "stop_buffer_atr",
        "fixed_reward_risk",
        "base_breakout_buffer_atr",
        "min_breakout_buffer_atr",
        "max_breakout_buffer_atr",
        "volatility_sensitivity",
        "min_volatility_ratio",
        "max_volatility_ratio",
        "retest_tolerance_atr",
        "max_breakout_chase_atr",
        "min_strength",
        "strength_min",
        "entry_price",
        "stop_price",
        "target_price",
    }
    return leaf in exact


def validate_contract_document(contract: dict[str, Any]) -> ResolutionStatus:
    missing = REQUIRED_CONTRACT_FIELDS - set(contract)
    if missing:
        msg = f"baseline contract missing required fields: {sorted(missing)}"
        raise BaselineValidationError(msg)
    unknown = set(contract) - REQUIRED_CONTRACT_FIELDS
    if unknown:
        msg = f"baseline contract has unknown fields: {sorted(unknown)}"
        raise BaselineValidationError(msg)

    if contract["schema_version"] != CONTRACT_SCHEMA_VERSION:
        msg = f"unsupported baseline contract schema_version: {contract['schema_version']!r}"
        raise BaselineValidationError(msg)

    status = parse_resolution_status(contract["resolution_status"])
    family_id = _require_string(contract["family_id"], field="family_id")
    family_code = _require_string(contract["family_code"], field="family_code")
    if family_code != ADAPTIVE_MTF_TREND_BREAKOUT_CODE:
        msg = f"unexpected family_code: {family_code!r}"
        raise BaselineValidationError(msg)
    if family_id != str(ADAPTIVE_MTF_TREND_BREAKOUT_ID):
        msg = "family_id does not match seeded Adaptive MTF family"
        raise BaselineValidationError(msg)

    _require_string(contract["baseline_code"], field="baseline_code")
    _require_string(contract["baseline_version"], field="baseline_version")

    authority = _require_object(contract["authority"], field="authority")
    missing_auth = REQUIRED_AUTHORITY_FIELDS - set(authority)
    if missing_auth:
        msg = f"authority missing required fields: {sorted(missing_auth)}"
        raise BaselineValidationError(msg)
    repo = _require_string(authority["repository"], field="authority.repository")
    commit = _require_commit(authority["commit_sha"], field="authority.commit_sha")
    if repo != PINNED_MOMO_REPOSITORY:
        msg = "authority.repository must be the pinned MOMO Quant repository"
        raise BaselineValidationError(msg)
    if commit != PINNED_MOMO_COMMIT:
        msg = "authority.commit_sha must match the pinned MOMO Quant commit"
        raise BaselineValidationError(msg)
    parse_evidence_classification(authority["evidence_class"])
    _require_git_blob_sha(authority["source_blob_sha"], field="authority.source_blob_sha")
    _require_string(authority["inspection_date"], field="authority.inspection_date")
    _require_string(authority["source_file_path"], field="authority.source_file_path")
    _require_string(authority["source_symbol_or_type"], field="authority.source_symbol_or_type")

    source_files = _require_list(contract["source_files"], field="source_files")
    source_tests = _require_list(contract["source_tests"], field="source_tests")
    if not source_files:
        msg = "source_files must be non-empty"
        raise BaselineValidationError(msg)
    if not source_tests:
        msg = "source_tests must be non-empty"
        raise BaselineValidationError(msg)

    unresolved = _require_list(contract["unresolved_items"], field="unresolved_items")
    protected = _require_object(contract["protected_semantics"], field="protected_semantics")
    missing_protected = PROTECTED_SEMANTIC_KEYS - set(protected)
    if missing_protected:
        msg = f"protected_semantics missing keys: {sorted(missing_protected)}"
        raise BaselineValidationError(msg)

    comparison = _require_object(contract["master_spec_comparison"], field="master_spec_comparison")
    if not comparison:
        msg = "master_spec_comparison must be non-empty"
        raise BaselineValidationError(msg)

    reject_local_path_leakage(contract, field="baseline_contract")
    _walk_reject_noncanonical_decimals(contract, field="baseline_contract")

    if status is ResolutionStatus.RESOLVED and unresolved:
        msg = "RESOLVED contract must have an empty unresolved_items array"
        raise BaselineVerificationError(msg)

    for key in PROTECTED_SEMANTIC_KEYS:
        entry = _require_object(protected[key], field=f"protected_semantics.{key}")
        resolved_flag = entry.get("resolved")
        if not isinstance(resolved_flag, bool):
            msg = f"protected_semantics.{key}.resolved must be a bool"
            raise BaselineValidationError(msg)
        if status is ResolutionStatus.RESOLVED and not resolved_flag:
            msg = f"RESOLVED contract has unresolved protected field: {key}"
            raise BaselineVerificationError(msg)

    return status


def validate_evidence_document(
    evidence: dict[str, Any],
    *,
    contract: dict[str, Any],
    status: ResolutionStatus,
) -> tuple[int, int]:
    claims = evidence.get("claims")
    if not isinstance(claims, list):
        msg = "source_evidence.claims must be a JSON array"
        raise BaselineValidationError(msg)
    if not claims:
        msg = "source_evidence.claims must be non-empty"
        raise BaselineValidationError(msg)

    claim_ids: list[str] = []
    contradiction_count = 0
    for index, raw in enumerate(claims):
        claim = _require_object(raw, field=f"claims[{index}]")
        missing = REQUIRED_EVIDENCE_FIELDS - set(claim)
        if missing:
            msg = f"evidence claim missing fields: {sorted(missing)}"
            raise BaselineValidationError(msg)
        claim_id = _require_string(claim["claim_id"], field="claim_id")
        claim_ids.append(claim_id)
        classification = parse_evidence_classification(claim["classification"])
        if classification is EvidenceClassification.CONTRADICTORY:
            contradiction_count += 1
        repo = _require_string(claim["repository"], field="repository")
        commit = _require_commit(claim["commit_sha"], field="commit_sha")
        if repo not in {PINNED_MOMO_REPOSITORY, "ZavierAhmed/Zorqen-Research"}:
            msg = f"evidence repository not recognized: {repo!r}"
            raise BaselineValidationError(msg)
        if repo == PINNED_MOMO_REPOSITORY and commit != PINNED_MOMO_COMMIT:
            msg = "MOMO evidence must use the pinned commit SHA"
            raise BaselineVerificationError(msg)
        file_path = claim["file_path"]
        if file_path is not None:
            _require_string(file_path, field="file_path")
            if ":\\" in str(file_path) or str(file_path).startswith("/Users/"):
                msg = "evidence file_path must not be a local absolute path"
                raise BaselineValidationError(msg)
        blob = claim["blob_sha"]
        if blob is not None:
            _require_git_blob_sha(blob, field="blob_sha")

    if len(set(claim_ids)) != len(claim_ids):
        msg = "duplicate evidence claim_id values are not allowed"
        raise BaselineValidationError(msg)
    if claim_ids != sorted(claim_ids):
        msg = "evidence claims must be sorted by claim_id"
        raise BaselineValidationError(msg)

    reject_local_path_leakage(evidence, field="source_evidence")

    if status is ResolutionStatus.RESOLVED:
        if not claims:
            msg = "RESOLVED contract requires source evidence"
            raise BaselineVerificationError(msg)
        _require_protected_evidence(claims, contract)

    return (
        len(_require_list(contract["unresolved_items"], field="unresolved_items")),
        contradiction_count,
    )


def _require_protected_evidence(claims: list[Any], contract: dict[str, Any]) -> None:
    by_id = {
        _require_string(c["claim_id"], field="claim_id"): c for c in claims if isinstance(c, dict)
    }
    protected = _require_object(contract["protected_semantics"], field="protected_semantics")
    for key in sorted(PROTECTED_SEMANTIC_KEYS):
        entry = _require_object(protected[key], field=f"protected_semantics.{key}")
        evidence_ids = _require_list(entry.get("evidence_ids", []), field=f"{key}.evidence_ids")
        if not evidence_ids:
            msg = f"RESOLVED protected field {key} requires evidence_ids"
            raise BaselineVerificationError(msg)
        authoritative_found = False
        for claim_id in evidence_ids:
            cid = _require_string(claim_id, field="evidence_ids item")
            claim = by_id.get(cid)
            if claim is None:
                msg = f"protected field {key} references unknown claim_id {cid!r}"
                raise BaselineVerificationError(msg)
            classification = parse_evidence_classification(claim["classification"])
            if classification in NON_AUTHORITATIVE_EVIDENCE:
                # Informational/illustrative rows may annotate a claim but cannot alone
                # satisfy protected semantics.
                continue
            if classification in AUTHORITATIVE_EVIDENCE:
                authoritative_found = True
        if not authoritative_found:
            msg = (
                f"protected field {key} lacks authoritative evidence "
                "(informational/illustrative evidence alone is insufficient)"
            )
            raise BaselineVerificationError(msg)

    # Timing and no-lookahead need executable + preferably test support.
    for critical in ("signal_timing", "no_lookahead"):
        entry = _require_object(protected[critical], field=f"protected_semantics.{critical}")
        evidence_ids = [
            _require_string(x, field="evidence_ids item")
            for x in _require_list(entry.get("evidence_ids", []), field="evidence_ids")
        ]
        classes = {
            parse_evidence_classification(by_id[cid]["classification"]) for cid in evidence_ids
        }
        if EvidenceClassification.AUTHORITATIVE_EXECUTABLE not in classes:
            msg = f"RESOLVED {critical} requires AUTHORITATIVE_EXECUTABLE evidence"
            raise BaselineVerificationError(msg)


def _hash_file_bytes(path: Path) -> str:
    return sha256_hex(path.read_bytes())


def verify_fixture_manifest(
    *,
    family_code: str,
    status: ResolutionStatus,
) -> str | None:
    root = fixture_root(family_code)
    manifest_path = root / "manifest.json"
    if status is not ResolutionStatus.RESOLVED:
        if manifest_path.exists():
            msg = "non-RESOLVED baselines must not ship behavioral parity fixtures"
            raise BaselineVerificationError(msg)
        return None
    if not manifest_path.is_file():
        msg = "RESOLVED baseline requires fixture manifest.json"
        raise BaselineVerificationError(msg)
    manifest = load_json_object(manifest_path, field="fixture_manifest")
    reject_local_path_leakage(manifest, field="fixture_manifest")
    cases = _require_list(manifest.get("cases"), field="manifest.cases")
    if not cases:
        msg = "fixture manifest cases must be non-empty"
        raise BaselineValidationError(msg)
    for index, raw in enumerate(cases):
        case = _require_object(raw, field=f"manifest.cases[{index}]")
        case_id = _require_string(case["case_id"], field="case_id")
        case_dir = root / case_id
        expected_path = case_dir / "expected.json"
        if not expected_path.is_file():
            msg = f"fixture case {case_id} missing expected.json"
            raise BaselineVerificationError(msg)
        expected = load_json_object(expected_path, field=f"{case_id}.expected")
        reject_local_path_leakage(expected, field=f"{case_id}.expected")
        expected_hash = _require_sha256(case["expected_hash"], field="expected_hash")
        actual_expected_hash = sha256_hex(canonical_json_bytes(expected))
        if expected_hash != actual_expected_hash:
            msg = f"fixture case {case_id} expected_hash mismatch"
            raise BaselineVerificationError(msg)
        for candle_key in ("execution_csv_hash", "context_csv_hash"):
            declared = case.get(candle_key)
            rel = "execution.csv" if candle_key.startswith("execution") else "context_1h.csv"
            candle_path = case_dir / rel
            if declared is None:
                if candle_path.exists():
                    msg = f"fixture case {case_id} has CSV but null {candle_key}"
                    raise BaselineVerificationError(msg)
                continue
            digest = _require_sha256(declared, field=candle_key)
            if not candle_path.is_file():
                msg = f"fixture case {case_id} missing {rel}"
                raise BaselineVerificationError(msg)
            if digest != _hash_file_bytes(candle_path):
                msg = f"fixture case {case_id} {candle_key} mismatch"
                raise BaselineVerificationError(msg)
        provenance = _require_object(case.get("provenance", {}), field="provenance")
        commit = _require_commit(provenance.get("commit_sha"), field="provenance.commit_sha")
        if commit != PINNED_MOMO_COMMIT:
            msg = "fixture provenance must cite the pinned MOMO commit"
            raise BaselineVerificationError(msg)
        # Decision-time safety: expected trace must not reference future context.
        decision_close = expected.get("decision_close_time")
        visible_context = expected.get("visible_context_count")
        if decision_close is not None:
            _require_string(decision_close, field="decision_close_time")
            if not str(decision_close).endswith("Z"):
                msg = "decision_close_time must be UTC ending in Z"
                raise BaselineValidationError(msg)
        if visible_context is not None and (
            isinstance(visible_context, bool) or not isinstance(visible_context, int)
        ):
            msg = "visible_context_count must be an int"
            raise BaselineValidationError(msg)

    # Manifest must itself be canonical (sorted keys when re-serialized).
    reloaded = load_json_object(manifest_path, field="fixture_manifest")
    on_disk = manifest_path.read_bytes()
    if on_disk != canonical_json_bytes(reloaded):
        msg = "fixture manifest.json must be canonical UTF-8 JSON"
        raise BaselineVerificationError(msg)
    return sha256_hex(on_disk)


def verify_approved_definition(
    *,
    baseline_dir: Path,
    contract: dict[str, Any],
    contract_hash: str,
    status: ResolutionStatus,
) -> str | None:
    definition_path = baseline_dir / DEFINITION_FILENAME
    if status is not ResolutionStatus.RESOLVED:
        if definition_path.exists():
            msg = "approved definition is forbidden unless resolution_status is RESOLVED"
            raise BaselineVerificationError(msg)
        return None
    if not definition_path.is_file():
        msg = "RESOLVED baseline requires approved_definition.json"
        raise BaselineVerificationError(msg)
    definition = parse_definition_file(definition_path)
    if definition.status is not DefinitionStatus.APPROVED:
        msg = "baseline definition status must be approved"
        raise BaselineVerificationError(msg)
    if definition.family_code != ADAPTIVE_MTF_TREND_BREAKOUT_CODE:
        msg = "approved definition family_code mismatch"
        raise BaselineVerificationError(msg)
    if definition.family_id != ADAPTIVE_MTF_TREND_BREAKOUT_ID:
        msg = "approved definition family_id mismatch"
        raise BaselineVerificationError(msg)
    if definition.source_spec_sha256 != contract_hash:
        msg = "approved definition source_spec_sha256 must equal baseline contract hash"
        raise BaselineVerificationError(msg)
    if definition.execution_timeframe.value != "5m":
        msg = "approved definition must use preferred execution timeframe 5m"
        raise BaselineVerificationError(msg)
    if len(definition.context_requirements) != 1:
        msg = "approved definition must declare exactly one context timeframe"
        raise BaselineVerificationError(msg)
    ctx = definition.context_requirements[0]
    if ctx.timeframe.value != "1h":
        msg = "approved definition context timeframe must be 1h for preferred 5m seed"
        raise BaselineVerificationError(msg)
    if definition.execution_warmup_bars != 165:
        msg = "approved definition execution_warmup_bars must be ComputeMinLtfBars=165"
        raise BaselineVerificationError(msg)
    if ctx.warmup_bars != 205:
        msg = "approved definition context warmup_bars must be htfSlow+htfSlope=205"
        raise BaselineVerificationError(msg)
    _ = contract  # reserved for future cross-checks against parameter inventory
    return hash_definition(definition)


def verify_baseline_family(family_code: str) -> BaselineVerificationResult:
    if family_code not in SUPPORTED_FAMILIES:
        msg = f"unknown baseline family: {family_code!r}"
        raise BaselineVerificationError(msg)

    baseline_dir = family_baseline_dir(family_code)
    contract = load_json_object(baseline_dir / CONTRACT_FILENAME, field="baseline_contract")
    evidence = load_json_object(baseline_dir / EVIDENCE_FILENAME, field="source_evidence")

    on_disk_contract = (baseline_dir / CONTRACT_FILENAME).read_bytes()
    if on_disk_contract != canonical_json_bytes(contract):
        msg = "baseline_contract.json must be canonical UTF-8 JSON"
        raise BaselineVerificationError(msg)
    on_disk_evidence = (baseline_dir / EVIDENCE_FILENAME).read_bytes()
    if on_disk_evidence != canonical_json_bytes(evidence):
        msg = "source_evidence.json must be canonical UTF-8 JSON"
        raise BaselineVerificationError(msg)

    status = validate_contract_document(contract)
    unresolved_count, contradiction_count = validate_evidence_document(
        evidence, contract=contract, status=status
    )
    contract_hash = hash_canonical_document(contract, field="baseline_contract_hash")
    evidence_hash = hash_canonical_document(evidence, field="source_evidence_hash")

    if status is ResolutionStatus.RESOLVED and contradiction_count > 0:
        msg = "RESOLVED baseline cannot retain CONTRADICTORY evidence rows"
        raise BaselineVerificationError(msg)

    fixture_hash = verify_fixture_manifest(family_code=family_code, status=status)
    definition_hash = verify_approved_definition(
        baseline_dir=baseline_dir,
        contract=contract,
        contract_hash=contract_hash,
        status=status,
    )

    provider_allowed = status is ResolutionStatus.RESOLVED and unresolved_count == 0
    authority = _require_object(contract["authority"], field="authority")
    return BaselineVerificationResult(
        ok=True,
        family_code=family_code,
        resolution_status=status.value,
        authority_repository=_require_string(authority["repository"], field="repository"),
        authority_commit=_require_commit(authority["commit_sha"], field="commit_sha"),
        baseline_version=_require_string(contract["baseline_version"], field="baseline_version"),
        baseline_contract_hash=contract_hash,
        source_evidence_hash=evidence_hash,
        fixture_manifest_hash=fixture_hash,
        strategy_definition_hash=definition_hash,
        unresolved_count=unresolved_count,
        contradiction_count=contradiction_count,
        provider_implementation_allowed=provider_allowed,
    )


def assert_no_strategy_provider_registered() -> None:
    """Milestone 1.3 must not register an Adaptive MTF strategy provider."""
    try:
        import zorqen_research.application.strategy_backtesting.provider as provider_mod
    except ImportError:
        return
    for name in dir(provider_mod):
        if "adaptive" in name.lower() or "mtf_trend" in name.lower():
            msg = "Adaptive MTF strategy provider must not be registered in Milestone 1.3"
            raise BaselineVerificationError(msg)


# Convenience alias used by CLI.
DEFAULT_FAMILY = ADAPTIVE_MTF_FAMILY_CODE
