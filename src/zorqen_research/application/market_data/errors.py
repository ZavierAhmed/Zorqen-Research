"""Candle access and integrity errors."""

from __future__ import annotations


class CandleAccessError(RuntimeError):
    """Base sanitized candle-access failure."""


class UnsupportedCandleDatasetError(CandleAccessError):
    """Dataset exists but its candle schema is not queryable."""


class DatasetIntegrityError(CandleAccessError):
    """Published dataset metadata failed integrity verification."""


class CandlePartitionIntegrityError(CandleAccessError):
    """Partition artifact bytes or metadata failed integrity verification."""


class CandleQueryValidationError(CandleAccessError, ValueError):
    """Invalid candle query parameters."""


class CandlePartitionNotFoundError(CandleAccessError, LookupError):
    """Requested symbol/timeframe partition is missing."""
