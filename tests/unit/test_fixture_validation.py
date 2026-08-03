"""Unit tests for fixture CSV validation and dataset schemas."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from zorqen_research.api.schemas.datasets import snapshot_to_detail
from zorqen_research.application.datasets.fixture_validation import validate_fixture_csv
from zorqen_research.domain.datasets import DatasetPartition, DatasetSnapshot, DatasetSnapshotStatus
from zorqen_research.domain.markets import Market
from zorqen_research.domain.symbols import Symbol
from zorqen_research.domain.timeframes import Timeframe

FIXTURE = (
    Path(__file__).resolve().parents[1] / "fixtures" / "market_data" / "btcusdt_1h_fixture.csv"
)


def test_fixture_csv_validates() -> None:
    result = validate_fixture_csv(FIXTURE.read_bytes())
    assert result.row_count == 5
    assert result.summary["passed"] is True


def test_fixture_csv_rejects_bad_ohlc() -> None:
    bad = b"open_time,open,high,low,close,volume\n2024-01-01T00:00:00Z,10,9,8,9,1\n"
    with pytest.raises(ValueError, match="high must be"):
        validate_fixture_csv(bad)


def test_dataset_schema_exposes_no_filesystem_paths() -> None:
    now = datetime(2024, 1, 1, tzinfo=UTC)
    snapshot_id = uuid4()
    snapshot = DatasetSnapshot(
        id=snapshot_id,
        name="demo",
        description=None,
        exchange=Market.BINANCE_FUTURES,
        status=DatasetSnapshotStatus.PUBLISHED,
        manifest_version="1",
        content_hash="a" * 64,
        total_rows=1,
        minimum_open_time=now,
        maximum_open_time=now,
        created_at=now,
        published_at=now,
        validation_summary={"passed": True},
        partitions=(
            DatasetPartition(
                id=uuid4(),
                dataset_snapshot_id=snapshot_id,
                symbol=Symbol(value="BTCUSDT"),
                timeframe=Timeframe.H1,
                artifact_key="sha256/aa/bb/" + ("c" * 64),
                sha256="c" * 64,
                byte_size=12,
                row_count=1,
                minimum_open_time=now,
                maximum_open_time=now,
                created_at=now,
            ),
        ),
    )
    payload = snapshot_to_detail(snapshot).model_dump()
    text = str(payload)
    assert "C:\\" not in text
    assert "/Users/" not in text
    assert "artifact_root" not in text
