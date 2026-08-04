"""Indicator-view domain errors."""

from __future__ import annotations


class IndicatorViewError(Exception):
    """Base error for bounded indicator decision views."""


class IndicatorViewValidationError(IndicatorViewError, ValueError):
    """Invalid indicator-view bundle, history, feed, or lookup construction."""
