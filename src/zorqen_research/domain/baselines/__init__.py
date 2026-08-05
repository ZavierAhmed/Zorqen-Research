"""Authoritative strategy-baseline domain types."""

from zorqen_research.domain.baselines.canonical import (
    canonical_json_bytes,
    hash_canonical_document,
    reject_local_path_leakage,
)
from zorqen_research.domain.baselines.enums import (
    AUTHORITATIVE_EVIDENCE,
    NON_AUTHORITATIVE_EVIDENCE,
    PROTECTED_SEMANTIC_KEYS,
    ComparisonResult,
    EvidenceClassification,
    ResolutionStatus,
    parse_comparison_result,
    parse_evidence_classification,
    parse_resolution_status,
)
from zorqen_research.domain.baselines.errors import (
    BaselineError,
    BaselineParseError,
    BaselineValidationError,
    BaselineVerificationError,
)

__all__ = [
    "AUTHORITATIVE_EVIDENCE",
    "NON_AUTHORITATIVE_EVIDENCE",
    "PROTECTED_SEMANTIC_KEYS",
    "BaselineError",
    "BaselineParseError",
    "BaselineValidationError",
    "BaselineVerificationError",
    "ComparisonResult",
    "EvidenceClassification",
    "ResolutionStatus",
    "canonical_json_bytes",
    "hash_canonical_document",
    "parse_comparison_result",
    "parse_evidence_classification",
    "parse_resolution_status",
    "reject_local_path_leakage",
]
