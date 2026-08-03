"""Binance kline import publication service."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from zorqen_research.application.audit.service import AuditEventService
from zorqen_research.application.datasets.manifest import build_and_hash_manifest
from zorqen_research.application.datasets.service import DatasetDuplicateError
from zorqen_research.application.market_data.client import (
    DEFAULT_KLINES_PAGE_LIMIT,
    MarketDataClient,
)
from zorqen_research.application.market_data.pagination import (
    assert_complete_coverage,
    fetch_klines_range,
)
from zorqen_research.application.market_data.ranges import parse_import_range
from zorqen_research.application.market_data.serialization import (
    CANONICAL_SCHEMA_VERSION,
    serialize_candles_csv,
)
from zorqen_research.domain.artifacts import MediaType
from zorqen_research.domain.audit import AuditEventAppendCommand
from zorqen_research.domain.datasets import DatasetPartition, DatasetSnapshot, DatasetSnapshotStatus
from zorqen_research.domain.markets import Market
from zorqen_research.domain.symbols import Symbol, parse_symbol
from zorqen_research.domain.timeframes import Timeframe, parse_timeframe
from zorqen_research.infrastructure.artifacts.local import LocalFilesystemArtifactStore
from zorqen_research.infrastructure.database.repositories.datasets import DatasetRepository

MANIFEST_VERSION_IMPORT = "2"
# Application-owned Binance provenance (not imported from the HTTP client).
BINANCE_PROVIDER = "binance"
BINANCE_KLINES_ENDPOINT_PATH = "/fapi/v1/klines"


@dataclass(frozen=True, slots=True)
class BinanceImportResult:
    snapshot_id: UUID
    content_hash: str
    created: bool
    symbol: str
    timeframe: str
    start: datetime
    end: datetime
    candle_count: int
    source_page_count: int
    normalized_sha256: str


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H%M%SZ")


def build_import_dataset_name(
    *,
    symbol: Symbol,
    timeframe: Timeframe,
    start: datetime,
    end: datetime,
    schema_version: str = CANONICAL_SCHEMA_VERSION,
) -> str:
    return (
        f"binance_futures_{symbol.value}_{timeframe.value}_"
        f"{_iso(start)}_{_iso(end)}_v{schema_version}"
    )


class BinanceImportService:
    """Fetch, validate, and publish Binance futures candle imports."""

    def __init__(
        self,
        session: AsyncSession,
        artifact_store: LocalFilesystemArtifactStore,
        client: MarketDataClient,
        *,
        max_candles: int = 100_000,
        page_limit: int = DEFAULT_KLINES_PAGE_LIMIT,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._session = session
        self._repo = DatasetRepository(session)
        self._audit = AuditEventService(session)
        self._artifacts = artifact_store
        self._client = client
        self._max_candles = max_candles
        self._page_limit = page_limit
        self._clock = clock or (lambda: datetime.now(UTC))

    async def import_klines(
        self,
        *,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
    ) -> BinanceImportResult:
        parsed_symbol = parse_symbol(symbol)
        parsed_tf = parse_timeframe(timeframe).value
        import_range = parse_import_range(
            start=start,
            end=end,
            timeframe=parsed_tf,
            now=self._clock(),
        )
        expected = import_range.expected_candle_count
        if expected > self._max_candles:
            msg = (
                f"Import expects {expected} candles which exceeds "
                f"ZORQEN_IMPORT_MAX_CANDLES={self._max_candles}"
            )
            raise ValueError(msg)

        fetch = fetch_klines_range(
            client_fetch=self._client.fetch_klines_page,
            symbol=parsed_symbol.value,
            import_range=import_range,
            page_limit=self._page_limit,
        )
        assert_complete_coverage(fetch.candles, import_range)

        # Publish raw pages then canonical CSV through the immutable store.
        source_page_meta: list[dict[str, Any]] = []
        for index, page in enumerate(fetch.pages):
            artifact = self._artifacts.publish_bytes(
                page.raw_bytes,
                media_type=MediaType.JSON,
                original_filename=f"binance_klines_page_{index:04d}.json",
            )
            source_page_meta.append(
                {
                    "artifact_key": artifact.key,
                    "sha256": artifact.sha256,
                    "byte_size": artifact.byte_size,
                    "requested_start": page.requested_start.astimezone(UTC)
                    .isoformat()
                    .replace("+00:00", "Z"),
                    "requested_end": page.requested_end.astimezone(UTC)
                    .isoformat()
                    .replace("+00:00", "Z"),
                    "requested_limit": page.requested_limit,
                    "returned_row_count": page.returned_row_count,
                    "page_index": index,
                }
            )

        csv_bytes = serialize_candles_csv(fetch.candles)
        normalized = self._artifacts.publish_bytes(
            csv_bytes,
            media_type=MediaType.CSV,
            original_filename=(
                f"{parsed_symbol.value}_{parsed_tf.value}_"
                f"{_iso(import_range.start)}_{_iso(import_range.end)}.csv"
            ),
        )

        dataset_name = build_import_dataset_name(
            symbol=parsed_symbol,
            timeframe=parsed_tf,
            start=import_range.start,
            end=import_range.end,
        )
        published_at = datetime.now(UTC)
        snapshot_id = uuid4()
        provenance = {
            "provider": BINANCE_PROVIDER,
            "market": Market.BINANCE_FUTURES.value,
            "data_type": "contract_klines",
            "endpoint_path": BINANCE_KLINES_ENDPOINT_PATH,
            "symbol": parsed_symbol.value,
            "timeframe": parsed_tf.value,
            "requested_start": import_range.start.astimezone(UTC)
            .isoformat()
            .replace("+00:00", "Z"),
            "requested_end": import_range.end.astimezone(UTC).isoformat().replace("+00:00", "Z"),
            "expected_candle_count": expected,
            "actual_candle_count": len(fetch.candles),
            "canonical_schema_version": CANONICAL_SCHEMA_VERSION,
            "source_pages": source_page_meta,
            "normalized_partition": {
                "artifact_key": normalized.key,
                "sha256": normalized.sha256,
                "byte_size": normalized.byte_size,
                "media_type": MediaType.CSV.value,
                "row_count": len(fetch.candles),
            },
        }
        validation_summary = {
            "passed": True,
            "checks": [
                "alignment",
                "closed_candles",
                "coverage",
                "ordering",
                "ohlc_bounds",
            ],
            "expected_candle_count": expected,
            "actual_candle_count": len(fetch.candles),
            "source_page_count": len(fetch.pages),
            "provenance": provenance,
        }

        provisional = DatasetSnapshot(
            id=snapshot_id,
            name=dataset_name,
            description=(
                f"Binance futures {parsed_symbol.value} {parsed_tf.value} "
                f"[{_iso(import_range.start)}, {_iso(import_range.end)})"
            ),
            exchange=Market.BINANCE_FUTURES,
            status=DatasetSnapshotStatus.PUBLISHED,
            manifest_version=MANIFEST_VERSION_IMPORT,
            content_hash=None,
            total_rows=len(fetch.candles),
            minimum_open_time=fetch.candles[0].open_time,
            maximum_open_time=fetch.candles[-1].open_time,
            created_at=published_at,
            published_at=published_at,
            validation_summary=validation_summary,
            partitions=(
                DatasetPartition(
                    id=uuid4(),
                    dataset_snapshot_id=snapshot_id,
                    symbol=parsed_symbol,
                    timeframe=parsed_tf,
                    artifact_key=normalized.key,
                    sha256=normalized.sha256,
                    byte_size=normalized.byte_size,
                    row_count=len(fetch.candles),
                    minimum_open_time=fetch.candles[0].open_time,
                    maximum_open_time=fetch.candles[-1].open_time,
                    created_at=published_at,
                ),
            ),
        )
        _document, content_hash, _encoded = build_and_hash_manifest(provisional)

        existing = await self._repo.get_by_name(dataset_name)
        if existing is not None:
            if (
                existing.status is DatasetSnapshotStatus.PUBLISHED
                and existing.content_hash == content_hash
            ):
                return BinanceImportResult(
                    snapshot_id=existing.id,
                    content_hash=content_hash,
                    created=False,
                    symbol=parsed_symbol.value,
                    timeframe=parsed_tf.value,
                    start=import_range.start,
                    end=import_range.end,
                    candle_count=existing.total_rows,
                    source_page_count=int(
                        (existing.validation_summary or {}).get("source_page_count", 0)
                    ),
                    normalized_sha256=existing.partitions[0].sha256 if existing.partitions else "",
                )
            msg = (
                f"Dataset {dataset_name!r} already exists with conflicting content "
                f"(status={existing.status.value}, content_hash={existing.content_hash!r})"
            )
            raise DatasetDuplicateError(msg)

        snapshot = await self._repo.create_published_snapshot(
            snapshot_id=snapshot_id,
            name=dataset_name,
            description=provisional.description,
            exchange=Market.BINANCE_FUTURES,
            manifest_version=MANIFEST_VERSION_IMPORT,
            content_hash=content_hash,
            total_rows=len(fetch.candles),
            minimum_open_time=fetch.candles[0].open_time,
            maximum_open_time=fetch.candles[-1].open_time,
            published_at=published_at,
            validation_summary=validation_summary,
            partitions=[
                {
                    "symbol": parsed_symbol.value,
                    "timeframe": parsed_tf.value,
                    "artifact_key": normalized.key,
                    "sha256": normalized.sha256,
                    "byte_size": normalized.byte_size,
                    "row_count": len(fetch.candles),
                    "minimum_open_time": fetch.candles[0].open_time,
                    "maximum_open_time": fetch.candles[-1].open_time,
                }
            ],
        )
        await self._audit.append(
            AuditEventAppendCommand(
                actor_type="system",
                action="dataset_snapshot.published",
                entity_type="dataset_snapshot",
                entity_id=str(snapshot.id),
                payload={
                    "provider": BINANCE_PROVIDER,
                    "market": Market.BINANCE_FUTURES.value,
                    "symbol": parsed_symbol.value,
                    "timeframe": parsed_tf.value,
                    "requested_start": provenance["requested_start"],
                    "requested_end": provenance["requested_end"],
                    "manifest_hash": content_hash,
                    "candle_count": len(fetch.candles),
                    "source_page_count": len(fetch.pages),
                    "normalized_artifact_hash": normalized.sha256,
                },
            )
        )
        await self._session.commit()
        return BinanceImportResult(
            snapshot_id=snapshot.id,
            content_hash=content_hash,
            created=True,
            symbol=parsed_symbol.value,
            timeframe=parsed_tf.value,
            start=import_range.start,
            end=import_range.end,
            candle_count=len(fetch.candles),
            source_page_count=len(fetch.pages),
            normalized_sha256=normalized.sha256,
        )
