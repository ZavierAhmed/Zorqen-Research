"""CLI for dataset fixture publication and Binance kline import."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime
from importlib.resources import as_file, files
from pathlib import Path

from zorqen_research.application.datasets.service import (
    DatasetDuplicateError,
    DatasetService,
)
from zorqen_research.application.market_data.import_service import BinanceImportService
from zorqen_research.core.config import get_settings
from zorqen_research.core.logging import configure_logging
from zorqen_research.infrastructure.artifacts.local import LocalFilesystemArtifactStore
from zorqen_research.infrastructure.binance.client import BinanceFuturesPublicClient
from zorqen_research.infrastructure.binance.errors import BinanceClientError
from zorqen_research.infrastructure.database.engine import (
    create_engine,
    dispose_engine,
    get_session_factory,
)

FIXTURE_RESOURCE = files("zorqen_research.datasets.fixtures").joinpath("btcusdt_1h_fixture.csv")


def _parse_utc(value: str) -> datetime:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        msg = "Timestamps must be timezone-aware UTC (e.g. 2026-06-01T00:00:00Z)"
        raise argparse.ArgumentTypeError(msg)
    return parsed


async def _publish_fixture(fixture_path: Path) -> int:
    settings = get_settings()
    configure_logging(settings.log_level)
    engine = create_engine(settings.database_url)
    session_factory = get_session_factory(engine)
    store = LocalFilesystemArtifactStore(settings.artifact_root_resolved)
    try:
        async with session_factory() as session:
            service = DatasetService(session, store)
            try:
                result = await service.publish_fixture(fixture_path=fixture_path)
            except DatasetDuplicateError as exc:
                print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
                return 2
            except Exception as exc:  # noqa: BLE001 — CLI boundary
                await session.rollback()
                print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
                return 1
            payload = {
                "ok": True,
                "created": result.created,
                "snapshot_id": str(result.snapshot_id),
                "manifest_hash": result.content_hash,
                "partition_count": result.partition_count,
                "total_rows": result.total_rows,
                "idempotent": not result.created,
            }
            print(json.dumps(payload, separators=(",", ":"), sort_keys=True))
            return 0
    finally:
        await dispose_engine(engine)


async def _import_binance(
    *,
    symbol: str,
    timeframe: str,
    start: datetime,
    end: datetime,
) -> int:
    settings = get_settings()
    configure_logging(settings.log_level)
    engine = create_engine(settings.database_url)
    session_factory = get_session_factory(engine)
    store = LocalFilesystemArtifactStore(settings.artifact_root_resolved)
    client = BinanceFuturesPublicClient(
        timeout_seconds=settings.binance_request_timeout_seconds,
        max_attempts=settings.binance_max_attempts,
        max_retry_delay_seconds=settings.binance_max_retry_delay_seconds,
    )
    try:
        async with session_factory() as session:
            service = BinanceImportService(
                session,
                store,
                client,
                max_candles=settings.import_max_candles,
            )
            try:
                result = await service.import_klines(
                    symbol=symbol,
                    timeframe=timeframe,
                    start=start,
                    end=end,
                )
            except DatasetDuplicateError as exc:
                print(str(exc), file=sys.stderr)
                print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
                return 2
            except (BinanceClientError, ValueError) as exc:
                await session.rollback()
                print(str(exc), file=sys.stderr)
                print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
                return 1
            except Exception as exc:  # noqa: BLE001 — CLI boundary
                await session.rollback()
                print(str(exc), file=sys.stderr)
                print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
                return 1
            payload = {
                "ok": True,
                "created": result.created,
                "snapshot_id": str(result.snapshot_id),
                "content_hash": result.content_hash,
                "symbol": result.symbol,
                "timeframe": result.timeframe,
                "start": result.start.isoformat().replace("+00:00", "Z"),
                "end": result.end.isoformat().replace("+00:00", "Z"),
                "candle_count": result.candle_count,
                "source_page_count": result.source_page_count,
                "normalized_sha256": result.normalized_sha256,
                "idempotent": not result.created,
            }
            print(json.dumps(payload, separators=(",", ":"), sort_keys=True))
            return 0
    finally:
        client.close()
        await dispose_engine(engine)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="zorqen-dataset",
        description="Dataset fixture publication and Binance public kline import",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    publish = sub.add_parser(
        "publish-fixture",
        help="Publish the deterministic BTCUSDT 1h local fixture dataset",
    )
    publish.add_argument(
        "--fixture-path",
        type=Path,
        default=None,
        help="Optional path to a fixture CSV (defaults to the packaged fixture)",
    )

    import_cmd = sub.add_parser(
        "import-binance-klines",
        help="Import closed Binance USDⓈ-M Futures klines into a published dataset",
    )
    import_cmd.add_argument("--symbol", required=True, help="Approved symbol, e.g. BTCUSDT")
    import_cmd.add_argument("--timeframe", required=True, help="Canonical timeframe, e.g. 1h")
    import_cmd.add_argument(
        "--start",
        required=True,
        type=_parse_utc,
        help="Inclusive UTC start aligned to the timeframe",
    )
    import_cmd.add_argument(
        "--end",
        required=True,
        type=_parse_utc,
        help="Exclusive UTC end aligned to the timeframe",
    )

    args = parser.parse_args(argv)
    if args.command == "publish-fixture":
        fixture_path = args.fixture_path
        if fixture_path is None:
            with as_file(FIXTURE_RESOURCE) as packaged:
                return asyncio.run(_publish_fixture(Path(packaged)))
        return asyncio.run(_publish_fixture(fixture_path))
    if args.command == "import-binance-klines":
        return asyncio.run(
            _import_binance(
                symbol=args.symbol,
                timeframe=args.timeframe,
                start=args.start,
                end=args.end,
            )
        )
    parser.error(f"Unknown command: {args.command}")
    return 2
