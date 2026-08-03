"""Read-only dataset API response schemas."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from zorqen_research.application.market_data.query import CandleQueryPage
from zorqen_research.application.market_data.serialization import format_canonical_decimal
from zorqen_research.domain.candles import Candle
from zorqen_research.domain.datasets import DatasetPartition, DatasetSnapshot


class ErrorResponse(BaseModel):
    detail: str


class DatasetPartitionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    symbol: str
    timeframe: str
    artifact_key: str
    sha256: str
    byte_size: int
    row_count: int
    minimum_open_time: datetime | None
    maximum_open_time: datetime | None
    created_at: datetime


class DatasetSnapshotSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    name: str
    description: str | None
    exchange: str
    status: str
    manifest_version: str
    content_hash: str
    total_rows: int
    minimum_open_time: datetime | None
    maximum_open_time: datetime | None
    created_at: datetime
    published_at: datetime
    validation_summary: dict[str, Any]
    partition_count: int = Field(ge=0)


class DatasetSnapshotDetailResponse(DatasetSnapshotSummaryResponse):
    partitions: list[DatasetPartitionResponse]


class DatasetListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[DatasetSnapshotSummaryResponse]
    count: int


class CandleResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    open_time: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    close_time: datetime
    quote_asset_volume: Decimal
    trade_count: int
    taker_buy_base_volume: Decimal
    taker_buy_quote_volume: Decimal

    @field_serializer(
        "open",
        "high",
        "low",
        "close",
        "volume",
        "quote_asset_volume",
        "taker_buy_base_volume",
        "taker_buy_quote_volume",
    )
    def serialize_decimal(self, value: Decimal) -> str:
        return format_canonical_decimal(value)

    @field_serializer("open_time", "close_time")
    def serialize_utc(self, value: datetime) -> str:
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


class CandlePageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    snapshot_id: UUID
    symbol: str
    timeframe: str
    partition_sha256: str
    count: int
    has_more: bool
    next_cursor: str | None
    items: list[CandleResponse]


def partition_to_response(partition: DatasetPartition) -> DatasetPartitionResponse:
    return DatasetPartitionResponse(
        id=partition.id,
        symbol=partition.symbol.value,
        timeframe=partition.timeframe.value,
        artifact_key=partition.artifact_key,
        sha256=partition.sha256,
        byte_size=partition.byte_size,
        row_count=partition.row_count,
        minimum_open_time=partition.minimum_open_time,
        maximum_open_time=partition.maximum_open_time,
        created_at=partition.created_at,
    )


def snapshot_to_summary(snapshot: DatasetSnapshot) -> DatasetSnapshotSummaryResponse:
    if snapshot.content_hash is None or snapshot.published_at is None:
        msg = "Published snapshot is missing content_hash or published_at"
        raise RuntimeError(msg)
    return DatasetSnapshotSummaryResponse(
        id=snapshot.id,
        name=snapshot.name,
        description=snapshot.description,
        exchange=snapshot.exchange.value,
        status=snapshot.status.value,
        manifest_version=snapshot.manifest_version,
        content_hash=snapshot.content_hash,
        total_rows=snapshot.total_rows,
        minimum_open_time=snapshot.minimum_open_time,
        maximum_open_time=snapshot.maximum_open_time,
        created_at=snapshot.created_at,
        published_at=snapshot.published_at,
        validation_summary=dict(snapshot.validation_summary),
        partition_count=len(snapshot.partitions),
    )


def snapshot_to_detail(snapshot: DatasetSnapshot) -> DatasetSnapshotDetailResponse:
    summary = snapshot_to_summary(snapshot)
    partitions = sorted(
        snapshot.partitions,
        key=lambda item: (item.symbol.value, item.timeframe.value),
    )
    return DatasetSnapshotDetailResponse(
        **summary.model_dump(),
        partitions=[partition_to_response(item) for item in partitions],
    )


def candle_to_response(candle: Candle) -> CandleResponse:
    return CandleResponse(
        open_time=candle.open_time,
        open=candle.open,
        high=candle.high,
        low=candle.low,
        close=candle.close,
        volume=candle.volume,
        close_time=candle.close_time,
        quote_asset_volume=candle.quote_asset_volume,
        trade_count=candle.trade_count,
        taker_buy_base_volume=candle.taker_buy_base_volume,
        taker_buy_quote_volume=candle.taker_buy_quote_volume,
    )


def candle_page_to_response(page: CandleQueryPage) -> CandlePageResponse:
    next_cursor = None
    if page.next_cursor is not None:
        next_cursor = page.next_cursor.astimezone(UTC).isoformat().replace("+00:00", "Z")
    return CandlePageResponse(
        snapshot_id=page.snapshot_id,
        symbol=page.symbol,
        timeframe=page.timeframe,
        partition_sha256=page.partition_sha256,
        count=page.count,
        has_more=page.has_more,
        next_cursor=next_cursor,
        items=[candle_to_response(item) for item in page.items],
    )
