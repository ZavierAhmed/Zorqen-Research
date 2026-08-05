"""Errors for authoritative strategy-baseline resolution."""

from __future__ import annotations


class BaselineError(RuntimeError):
    """Base error for baseline-contract failures."""


class BaselineValidationError(BaselineError, ValueError):
    """Invalid baseline contract, evidence, or fixture document."""


class BaselineParseError(BaselineError, ValueError):
    """Malformed or rejected baseline JSON document."""


class BaselineVerificationError(BaselineError, ValueError):
    """Checked-in baseline evidence failed verification gates."""
