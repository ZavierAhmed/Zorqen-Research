"""Backtest domain errors."""

from __future__ import annotations


class BacktestError(RuntimeError):
    """Base backtest failure."""


class BacktestValidationError(BacktestError, ValueError):
    """Invalid policy, intent, or candle input."""


class BacktestExecutionError(BacktestError):
    """Simulation cannot complete under the configured policy."""
