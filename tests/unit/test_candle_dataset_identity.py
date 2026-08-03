"""Unit tests for supported candle dataset identity checks."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from zorqen_research.application.market_data.errors import (
    DatasetIntegrityError,
    UnsupportedCandleDatasetError,
)
from zorqen_research.application.market_data.integrity import assert_supported_candle_dataset
from zorqen_research.application.market_data.serialization import CANONICAL_SCHEMA_VERSION
from zorqen_research.domain.datasets import DatasetSnapshot, DatasetSnapshotStatus
from zorqen_research.domain.markets import Market


def _snapshot(**overrides) -> DatasetSnapshot:
    base = {
        "id": uuid4(),
        "name": "test",
        "description": None,
        "exchange": Market.BINANCE_FUTURES,
        "status": DatasetSnapshotStatus.PUBLISHED,
        "manifest_version": "2",
        "content_hash": "a" * 64,
        "total_rows": 1,
        "minimum_open_time": datetime(2026, 6, 1, tzinfo=UTC),
        "maximum_open_time": datetime(2026, 6, 1, tzinfo=UTC),
        "created_at": datetime(2026, 6, 1, tzinfo=UTC),
        "published_at": datetime(2026, 6, 1, tzinfo=UTC),
        "validation_summary": {
            "provenance": {
                "provider": "binance",
                "market": "binance_futures",
                "data_type": "contract_klines",
                "endpoint_path": "/fapi/v1/klines",
                "canonical_schema_version": CANONICAL_SCHEMA_VERSION,
            }
        },
        "partitions": (),
    }
    base.update(overrides)
    return DatasetSnapshot(**base)


def test_assert_supported_accepts_valid_identity() -> None:
    provenance = assert_supported_candle_dataset(_snapshot())
    assert provenance["endpoint_path"] == "/fapi/v1/klines"


def test_assert_supported_rejects_wrong_endpoint_as_integrity() -> None:
    snap = _snapshot(
        validation_summary={
            "provenance": {
                "provider": "binance",
                "market": "binance_futures",
                "data_type": "contract_klines",
                "endpoint_path": "/wrong",
                "canonical_schema_version": CANONICAL_SCHEMA_VERSION,
            }
        }
    )
    with pytest.raises(DatasetIntegrityError, match="endpoint"):
        assert_supported_candle_dataset(snap)


def test_assert_supported_rejects_manifest_v1_as_unsupported() -> None:
    with pytest.raises(UnsupportedCandleDatasetError):
        assert_supported_candle_dataset(_snapshot(manifest_version="1"))
