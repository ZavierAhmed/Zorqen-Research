"""Errors for multi-timeframe strategy backtest bridging."""

from __future__ import annotations


class StrategyBacktestError(Exception):
    """Base error for multi-timeframe strategy backtest bridging."""


class StrategyBacktestValidationError(StrategyBacktestError):
    """Sanitized validation failure for MTF backtest inputs or views."""
