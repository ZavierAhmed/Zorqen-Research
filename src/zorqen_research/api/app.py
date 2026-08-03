"""FastAPI application factory and process entry point."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel

import zorqen_research.infrastructure.database.models  # noqa: F401
from zorqen_research import __version__
from zorqen_research.api.routes import health, strategy_families
from zorqen_research.core.config import Settings, get_settings
from zorqen_research.core.logging import configure_logging
from zorqen_research.infrastructure.database.engine import (
    create_engine,
    dispose_engine,
    get_session_factory,
)


class RootMetadata(BaseModel):
    """Minimal service metadata for operators."""

    service: str = "zorqen-research-api"
    version: str
    environment: str
    message: str = "Zorqen Research foundation API. Trading execution is outside this application."


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    app_settings = settings or get_settings()
    configure_logging(app_settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = create_engine(app_settings.database_url)
        app.state.engine = engine
        app.state.session_factory = get_session_factory(engine)
        app.state.settings = app_settings
        try:
            yield
        finally:
            await dispose_engine(engine)
            app.state.engine = None
            app.state.session_factory = None

    app = FastAPI(
        title="Zorqen Research API",
        version=__version__,
        description=(
            "Foundation API for Zorqen Research. "
            "This service does not execute trades or connect to exchanges."
        ),
        lifespan=lifespan,
    )
    app.include_router(health.router)
    app.include_router(strategy_families.router)

    @app.get("/", response_model=RootMetadata, tags=["metadata"])
    async def root() -> RootMetadata:
        return RootMetadata(version=__version__, environment=app_settings.environment)

    return app


def run() -> None:
    """Run the API with uvicorn (console script entry point)."""
    import uvicorn

    settings = get_settings()
    configure_logging(settings.log_level)
    uvicorn.run(
        "zorqen_research.api.app:create_app",
        factory=True,
        host=settings.api_host,
        port=settings.api_port,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    run()
