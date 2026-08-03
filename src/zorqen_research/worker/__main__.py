"""Worker process entry point.

Usage:
    uv run python -m zorqen_research.worker
    uv run python -m zorqen_research.worker --check
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from zorqen_research.core.config import get_settings
from zorqen_research.core.logging import configure_logging
from zorqen_research.worker.service import WorkerService


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse worker CLI arguments."""
    parser = argparse.ArgumentParser(description="Zorqen Research worker process")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify configuration and PostgreSQL connectivity, then exit",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run the worker or one-shot check mode."""
    args = parse_args(argv)
    settings = get_settings()
    configure_logging(settings.log_level)
    service = WorkerService(settings)

    if args.check:
        return asyncio.run(service.check())

    asyncio.run(service.run())
    return 0


if __name__ == "__main__":
    sys.exit(main())
