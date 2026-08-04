"""Errors for deterministic candle resampling and alignment."""

from __future__ import annotations


class ResamplingError(Exception):
    """Base error for timeframe resampling and alignment."""


class ResamplingValidationError(ResamplingError):
    """Sanitized validation failure for resampling or alignment inputs."""


class AlignmentValidationError(ResamplingError):
    """Sanitized validation failure for no-lookahead context alignment."""
