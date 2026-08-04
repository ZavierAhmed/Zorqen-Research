"""Indicator domain errors."""

from __future__ import annotations


class IndicatorError(Exception):
    """Base error for the indicator foundation."""


class IndicatorValidationError(IndicatorError, ValueError):
    """Invalid indicator input, period, or result construction."""
