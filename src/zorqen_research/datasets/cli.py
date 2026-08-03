"""CLI helpers for dataset fixture publication."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from importlib.resources import as_file, files
from pathlib import Path

from zorqen_research.application.datasets.service import (
    DatasetDuplicateError,
    DatasetService,
)
from zorqen_research.core.config import get_settings
from zorqen_research.core.logging import configure_logging
from zorqen_research.infrastructure.artifacts.local import LocalFilesystemArtifactStore
from zorqen_research.infrastructure.database.engine import (
    create_engine,
    dispose_engine,
    get_session_factory,
)

FIXTURE_RESOURCE = files("zorqen_research.datasets.fixtures").joinpath("btcusdt_1h_fixture.csv")


def default_fixture_path() -> Path:
    """Resolve the packaged fixture to a filesystem path."""
    with as_file(FIXTURE_RESOURCE) as path:
        return Path(path)


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="zorqen-dataset",
        description="Dataset fixture publication for Zorqen Research",
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
    args = parser.parse_args(argv)
    if args.command == "publish-fixture":
        fixture_path = args.fixture_path
        if fixture_path is None:
            with as_file(FIXTURE_RESOURCE) as packaged:
                return asyncio.run(_publish_fixture(Path(packaged)))
        return asyncio.run(_publish_fixture(fixture_path))
    parser.error(f"Unknown command: {args.command}")
    return 2
