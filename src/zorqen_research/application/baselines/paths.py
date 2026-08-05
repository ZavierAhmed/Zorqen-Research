"""Path resolution for checked-in Adaptive MTF baseline artifacts."""

from __future__ import annotations

from pathlib import Path

from zorqen_research.domain.baselines.errors import BaselineValidationError

ADAPTIVE_MTF_FAMILY_CODE = "adaptive_mtf_trend_breakout"
BASELINE_VERSION = "v1"
SUPPORTED_FAMILIES: frozenset[str] = frozenset({ADAPTIVE_MTF_FAMILY_CODE})

CONTRACT_FILENAME = "baseline_contract.json"
EVIDENCE_FILENAME = "source_evidence.json"
DEFINITION_FILENAME = "approved_definition.json"


def repository_root() -> Path:
    """Locate the Zorqen Research repository root from this package path."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").is_file() and (parent / "src" / "zorqen_research").is_dir():
            return parent
    msg = "unable to locate repository root containing baselines"
    raise BaselineValidationError(msg)


def baselines_root() -> Path:
    root = repository_root() / "baselines"
    if not root.is_dir():
        msg = "baselines directory is missing"
        raise BaselineValidationError(msg)
    return root


def family_baseline_dir(family_code: str, *, version: str = BASELINE_VERSION) -> Path:
    if family_code not in SUPPORTED_FAMILIES:
        msg = f"unknown baseline family: {family_code!r}"
        raise BaselineValidationError(msg)
    path = baselines_root() / family_code / version
    if not path.is_dir():
        msg = f"baseline directory missing for family {family_code!r}"
        raise BaselineValidationError(msg)
    return path


def fixture_root(family_code: str, *, version: str = BASELINE_VERSION) -> Path:
    if family_code not in SUPPORTED_FAMILIES:
        msg = f"unknown baseline family: {family_code!r}"
        raise BaselineValidationError(msg)
    path = repository_root() / "tests" / "fixtures" / family_code / version
    return path
