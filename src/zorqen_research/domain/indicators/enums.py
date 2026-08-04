"""Stable indicator code identifiers."""

from __future__ import annotations

from enum import StrEnum


class IndicatorCode(StrEnum):
    """Explicit stable indicator identifiers — no aliases."""

    EMA_CLOSE = "ema_close"
    TRUE_RANGE = "true_range"
    WILDER_ATR = "wilder_atr"
    ROLLING_HIGHEST = "rolling_highest"
    ROLLING_LOWEST = "rolling_lowest"
    PRIOR_ROLLING_HIGHEST = "prior_rolling_highest"
    PRIOR_ROLLING_LOWEST = "prior_rolling_lowest"
