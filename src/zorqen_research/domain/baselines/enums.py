"""Enums for baseline-resolution authority and status."""

from __future__ import annotations

from enum import StrEnum

from zorqen_research.domain.baselines.errors import BaselineValidationError


class ResolutionStatus(StrEnum):
    RESOLVED = "RESOLVED"
    UNRESOLVED = "UNRESOLVED"
    CONTRADICTORY = "CONTRADICTORY"
    NOT_IMPLEMENTED_IN_MOMO = "NOT_IMPLEMENTED_IN_MOMO"


class EvidenceClassification(StrEnum):
    AUTHORITATIVE_EXECUTABLE = "AUTHORITATIVE_EXECUTABLE"
    AUTHORITATIVE_TEST = "AUTHORITATIVE_TEST"
    AUTHORITATIVE_FROZEN_DEFINITION = "AUTHORITATIVE_FROZEN_DEFINITION"
    INFORMATIONAL_DEFAULT = "INFORMATIONAL_DEFAULT"
    LEGACY_OR_DISABLED = "LEGACY_OR_DISABLED"
    ILLUSTRATIVE_ONLY = "ILLUSTRATIVE_ONLY"
    CONTRADICTORY = "CONTRADICTORY"
    MISSING = "MISSING"


class ComparisonResult(StrEnum):
    MATCH = "MATCH"
    DIFFERENT = "DIFFERENT"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
    AMBIGUOUS = "AMBIGUOUS"
    NO_AUTHORITATIVE_EVIDENCE = "NO_AUTHORITATIVE_EVIDENCE"


# Evidence classes that can satisfy a protected RESOLVED claim.
AUTHORITATIVE_EVIDENCE: frozenset[EvidenceClassification] = frozenset(
    {
        EvidenceClassification.AUTHORITATIVE_EXECUTABLE,
        EvidenceClassification.AUTHORITATIVE_TEST,
        EvidenceClassification.AUTHORITATIVE_FROZEN_DEFINITION,
    }
)

# Classifications that cannot alone establish executable behavior.
NON_AUTHORITATIVE_EVIDENCE: frozenset[EvidenceClassification] = frozenset(
    {
        EvidenceClassification.INFORMATIONAL_DEFAULT,
        EvidenceClassification.LEGACY_OR_DISABLED,
        EvidenceClassification.ILLUSTRATIVE_ONLY,
        EvidenceClassification.CONTRADICTORY,
        EvidenceClassification.MISSING,
    }
)

PROTECTED_SEMANTIC_KEYS: frozenset[str] = frozenset(
    {
        "signal_timing",
        "direction",
        "required_indicators",
        "warmup",
        "entry",
        "stop",
        "target",
        "retest_state",
        "volatility_eligibility",
        "no_lookahead",
    }
)


def parse_resolution_status(value: object) -> ResolutionStatus:
    if not isinstance(value, str):
        msg = "resolution_status must be a string"
        raise BaselineValidationError(msg)
    try:
        return ResolutionStatus(value)
    except ValueError as exc:
        msg = f"Unsupported resolution_status: {value!r}"
        raise BaselineValidationError(msg) from exc


def parse_evidence_classification(value: object) -> EvidenceClassification:
    if not isinstance(value, str):
        msg = "evidence classification must be a string"
        raise BaselineValidationError(msg)
    try:
        return EvidenceClassification(value)
    except ValueError as exc:
        msg = f"Unsupported evidence classification: {value!r}"
        raise BaselineValidationError(msg) from exc


def parse_comparison_result(value: object) -> ComparisonResult:
    if not isinstance(value, str):
        msg = "comparison result must be a string"
        raise BaselineValidationError(msg)
    try:
        return ComparisonResult(value)
    except ValueError as exc:
        msg = f"Unsupported comparison result: {value!r}"
        raise BaselineValidationError(msg) from exc
