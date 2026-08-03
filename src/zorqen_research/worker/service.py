"""Idle worker service loop with clean shutdown handling."""

from __future__ import annotations

import asyncio
import logging
import signal
from types import FrameType

from sqlalchemy.ext.asyncio import AsyncEngine

from zorqen_research.core.config import Settings
from zorqen_research.infrastructure.database.engine import (
    check_database_ready,
    create_engine,
    dispose_engine,
)

logger = logging.getLogger(__name__)


class WorkerService:
    """Foundation worker that idles until later milestones add job processing."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._stop_event = asyncio.Event()
        self._engine: AsyncEngine | None = None

    async def check(self) -> int:
        """
        One-shot readiness check.

        Returns 0 when PostgreSQL is reachable, nonzero otherwise.
        """
        engine = create_engine(self._settings.database_url)
        try:
            ready = await check_database_ready(engine)
            if ready:
                logger.info("Worker check: PostgreSQL is reachable")
                return 0
            logger.error("Worker check: PostgreSQL is unavailable")
            return 1
        finally:
            await dispose_engine(engine)

    async def run(self) -> None:
        """Run the idle service loop until a shutdown signal is received."""
        self._engine = create_engine(self._settings.database_url)
        self._install_signal_handlers()
        logger.info(
            "Worker started (idle interval=%.1fs). No research jobs are processed yet.",
            self._settings.worker_idle_interval_seconds,
        )
        try:
            while not self._stop_event.is_set():
                ready = await check_database_ready(self._engine)
                if ready:
                    logger.debug("Worker idle tick: database healthy")
                else:
                    logger.warning("Worker idle tick: database unhealthy")
                try:
                    await asyncio.wait_for(
                        self._stop_event.wait(),
                        timeout=self._settings.worker_idle_interval_seconds,
                    )
                except TimeoutError:
                    continue
        finally:
            await dispose_engine(self._engine)
            self._engine = None
            logger.info("Worker shut down cleanly")

    def request_shutdown(self) -> None:
        """Request a clean shutdown of the idle loop."""
        self._stop_event.set()

    def _install_signal_handlers(self) -> None:
        loop = asyncio.get_running_loop()

        def _handler(signum: int, _frame: FrameType | None) -> None:
            logger.info("Received signal %s; shutting down worker", signum)
            self.request_shutdown()

        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, self.request_shutdown)
            except NotImplementedError:
                # Windows: add_signal_handler is not fully supported for all signals.
                signal.signal(sig, _handler)
