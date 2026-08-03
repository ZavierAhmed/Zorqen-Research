"""Read-only candle query service with open-time cursor pagination."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from zorqen_research.application.datasets.service import DatasetNotFoundError, DatasetService
from zorqen_research.application.market_data.errors import (
    CandleQueryValidationError,
    DatasetIntegrityError,
    UnsupportedCandleDatasetError,
)
from zorqen_research.application.market_data.integrity import (
    VerifiedCandleDataset,
    assert_supported_candle_dataset,
    verify_candle_dataset,
)
from zorqen_research.application.market_data.ranges import assert_aligned
from zorqen_research.application.market_data.reader import CandlePartitionReader
from zorqen_research.domain.candles import Candle
from zorqen_research.domain.symbols import Symbol, parse_symbol
from zorqen_research.domain.timeframes import Timeframe, parse_timeframe
from zorqen_research.infrastructure.artifacts.local import LocalFilesystemArtifactStore

DEFAULT_CANDLE_LIMIT = 1000
MAX_CANDLE_LIMIT = 5000
MIN_CANDLE_LIMIT = 1


@dataclass(frozen=True, slots=True)
class CandleQuery:
    snapshot_id: UUID
    symbol: Symbol
    timeframe: Timeframe
    start: datetime | None = None
    end: datetime | None = None
    after: datetime | None = None
    limit: int = DEFAULT_CANDLE_LIMIT


@dataclass(frozen=True, slots=True)
class CandleQueryPage:
    snapshot_id: UUID
    symbol: str
    timeframe: str
    partition_sha256: str
    count: int
    has_more: bool
    next_cursor: datetime | None
    items: tuple[Candle, ...]


@dataclass(frozen=True, slots=True)
class SnapshotVerificationResult:
    ok: bool
    snapshot_id: UUID
    content_hash: str
    manifest_version: str
    partition_count: int
    verified_partition_count: int
    candle_count: int
    source_page_count: int
    verified_artifact_count: int
    minimum_open_time: datetime | None
    maximum_open_time: datetime | None
    unsupported: bool = False
    message: str | None = None


def _require_canonical_utc(value: datetime, *, field: str) -> datetime:
    if value.tzinfo is None:
        msg = f"{field} must be timezone-aware UTC"
        raise CandleQueryValidationError(msg)
    if value.utcoffset() != timedelta(0):
        msg = f"{field} must have a zero UTC offset"
        raise CandleQueryValidationError(msg)
    return value.astimezone(UTC)


def build_candle_query(
    *,
    snapshot_id: UUID,
    symbol: str,
    timeframe: str,
    start: datetime | None = None,
    end: datetime | None = None,
    after: datetime | None = None,
    limit: int = DEFAULT_CANDLE_LIMIT,
) -> CandleQuery:
    try:
        parsed_symbol = parse_symbol(symbol)
        parsed_tf = parse_timeframe(timeframe).value
    except ValueError as exc:
        raise CandleQueryValidationError(str(exc)) from exc

    if not isinstance(limit, int) or isinstance(limit, bool):
        msg = "limit must be an integer"
        raise CandleQueryValidationError(msg)
    if limit < MIN_CANDLE_LIMIT or limit > MAX_CANDLE_LIMIT:
        msg = f"limit must be between {MIN_CANDLE_LIMIT} and {MAX_CANDLE_LIMIT}"
        raise CandleQueryValidationError(msg)

    start_utc = None
    end_utc = None
    after_utc = None
    try:
        if start is not None:
            start_utc = assert_aligned(
                _require_canonical_utc(start, field="start"),
                parsed_tf,
                field="start",
            )
        if end is not None:
            end_utc = assert_aligned(
                _require_canonical_utc(end, field="end"),
                parsed_tf,
                field="end",
            )
        if after is not None:
            after_utc = assert_aligned(
                _require_canonical_utc(after, field="after"),
                parsed_tf,
                field="after",
            )
    except ValueError as exc:
        raise CandleQueryValidationError(str(exc)) from exc

    if start_utc is not None and end_utc is not None and not start_utc < end_utc:
        msg = "start must be strictly less than end"
        raise CandleQueryValidationError(msg)
    if after_utc is not None and start_utc is not None and after_utc < start_utc:
        msg = "after cursor must not be before start"
        raise CandleQueryValidationError(msg)
    if after_utc is not None and end_utc is not None and after_utc >= end_utc:
        msg = "after cursor must be strictly before end"
        raise CandleQueryValidationError(msg)

    return CandleQuery(
        snapshot_id=snapshot_id,
        symbol=parsed_symbol,
        timeframe=parsed_tf,
        start=start_utc,
        end=end_utc,
        after=after_utc,
        limit=limit,
    )


def _filter_candles(candles: tuple[Candle, ...], query: CandleQuery) -> list[Candle]:
    selected: list[Candle] = []
    for candle in candles:
        open_time = candle.open_time
        if query.start is not None and open_time < query.start:
            continue
        if query.end is not None and open_time >= query.end:
            continue
        if query.after is not None and open_time <= query.after:
            continue
        selected.append(candle)
    return selected


def paginate_candles(candles: tuple[Candle, ...], query: CandleQuery) -> CandleQueryPage:
    matching = _filter_candles(candles, query)
    page = matching[: query.limit]
    has_more = len(matching) > query.limit
    next_cursor = page[-1].open_time if has_more and page else None
    return CandleQueryPage(
        snapshot_id=query.snapshot_id,
        symbol=query.symbol.value,
        timeframe=query.timeframe.value,
        partition_sha256="",  # filled by service
        count=len(page),
        has_more=has_more,
        next_cursor=next_cursor,
        items=tuple(page),
    )


class CandleQueryService:
    """Verified candle query and snapshot verification."""

    def __init__(
        self,
        session: AsyncSession,
        artifact_store: LocalFilesystemArtifactStore,
        reader: CandlePartitionReader,
    ) -> None:
        self._datasets = DatasetService(session, artifact_store)
        self._artifacts = artifact_store
        self._reader = reader

    async def _load_verified(
        self,
        *,
        snapshot_id: UUID,
        symbol: Symbol,
        timeframe: Timeframe,
    ) -> VerifiedCandleDataset:
        try:
            snapshot = await self._datasets.get_published(snapshot_id)
        except DatasetNotFoundError:
            raise
        return verify_candle_dataset(
            snapshot,
            symbol=symbol,
            timeframe=timeframe,
            artifact_store=self._artifacts,
            reader=self._reader,
        )

    async def query(self, query: CandleQuery) -> CandleQueryPage:
        verified = await self._load_verified(
            snapshot_id=query.snapshot_id,
            symbol=query.symbol,
            timeframe=query.timeframe,
        )
        page = paginate_candles(verified.verified_partition.candles, query)
        return CandleQueryPage(
            snapshot_id=page.snapshot_id,
            symbol=page.symbol,
            timeframe=page.timeframe,
            partition_sha256=verified.verified_partition.sha256,
            count=page.count,
            has_more=page.has_more,
            next_cursor=page.next_cursor,
            items=page.items,
        )

    async def verify_snapshot(self, snapshot_id: UUID) -> SnapshotVerificationResult:
        try:
            snapshot = await self._datasets.get_published(snapshot_id)
        except DatasetNotFoundError:
            raise

        try:
            assert_supported_candle_dataset(snapshot)
        except UnsupportedCandleDatasetError as exc:
            return SnapshotVerificationResult(
                ok=False,
                snapshot_id=snapshot.id,
                content_hash=snapshot.content_hash or "",
                manifest_version=snapshot.manifest_version,
                partition_count=len(snapshot.partitions),
                verified_partition_count=0,
                candle_count=0,
                source_page_count=0,
                verified_artifact_count=0,
                minimum_open_time=snapshot.minimum_open_time,
                maximum_open_time=snapshot.maximum_open_time,
                unsupported=True,
                message=str(exc),
            )

        if len(snapshot.partitions) != 1:
            msg = "Supported candle datasets must have exactly one partition in this milestone"
            raise DatasetIntegrityError(msg)
        partition = snapshot.partitions[0]
        verified = await self._load_verified(
            snapshot_id=snapshot_id,
            symbol=partition.symbol,
            timeframe=partition.timeframe,
        )
        # Normalized partition + each source page.
        verified_artifacts = 1 + verified.verified_source_page_count
        return SnapshotVerificationResult(
            ok=True,
            snapshot_id=snapshot.id,
            content_hash=verified.content_hash,
            manifest_version=snapshot.manifest_version,
            partition_count=len(snapshot.partitions),
            verified_partition_count=1,
            candle_count=verified.verified_partition.row_count,
            source_page_count=verified.verified_source_page_count,
            verified_artifact_count=verified_artifacts,
            minimum_open_time=verified.verified_partition.minimum_open_time,
            maximum_open_time=verified.verified_partition.maximum_open_time,
            unsupported=False,
            message=None,
        )
