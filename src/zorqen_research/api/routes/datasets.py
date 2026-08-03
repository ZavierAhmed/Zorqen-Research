"""Read-only dataset API routes."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from zorqen_research.api.dependencies import get_db_session
from zorqen_research.api.schemas.datasets import (
    CandlePageResponse,
    DatasetListResponse,
    DatasetSnapshotDetailResponse,
    ErrorResponse,
    candle_page_to_response,
    snapshot_to_detail,
    snapshot_to_summary,
)
from zorqen_research.application.datasets.service import (
    DatasetNotFoundError,
    DatasetService,
)
from zorqen_research.application.market_data.errors import (
    CandlePartitionIntegrityError,
    CandlePartitionNotFoundError,
    CandleQueryValidationError,
    DatasetIntegrityError,
    UnsupportedCandleDatasetError,
)
from zorqen_research.application.market_data.query import (
    DEFAULT_CANDLE_LIMIT,
    MAX_CANDLE_LIMIT,
    CandleQueryService,
    build_candle_query,
)
from zorqen_research.core.config import Settings
from zorqen_research.infrastructure.artifacts.candle_partition_reader import (
    LocalCandlePartitionReader,
)
from zorqen_research.infrastructure.artifacts.local import LocalFilesystemArtifactStore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/datasets", tags=["datasets"])


def _artifact_store(request: Request) -> LocalFilesystemArtifactStore:
    settings: Settings = request.app.state.settings
    return LocalFilesystemArtifactStore(settings.artifact_root_configured)


def get_dataset_service(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DatasetService:
    return DatasetService(session, _artifact_store(request))


def get_candle_query_service(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CandleQueryService:
    store = _artifact_store(request)
    reader = LocalCandlePartitionReader(store)
    return CandleQueryService(session, store, reader)


@router.get(
    "",
    response_model=DatasetListResponse,
    summary="List published dataset snapshots",
)
async def list_datasets(
    service: Annotated[DatasetService, Depends(get_dataset_service)],
) -> DatasetListResponse:
    try:
        snapshots = await service.list_published()
    except Exception:
        logger.exception("Failed to list published datasets")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Dataset registry is temporarily unavailable.",
        ) from None
    items = [snapshot_to_summary(item) for item in snapshots]
    return DatasetListResponse(items=items, count=len(items))


@router.get(
    "/{snapshot_id}",
    response_model=DatasetSnapshotDetailResponse,
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ErrorResponse},
    },
    summary="Get one published dataset snapshot",
)
async def get_dataset(
    snapshot_id: UUID,
    service: Annotated[DatasetService, Depends(get_dataset_service)],
) -> DatasetSnapshotDetailResponse:
    try:
        snapshot = await service.get_published(snapshot_id)
    except DatasetNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset snapshot not found.",
        ) from None
    except Exception:
        logger.exception("Failed to load dataset snapshot_id=%s", snapshot_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Dataset registry is temporarily unavailable.",
        ) from None
    return snapshot_to_detail(snapshot)


@router.get(
    "/{snapshot_id}/manifest",
    response_model=dict[str, Any],
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ErrorResponse},
    },
    summary="Get the canonical manifest for a published snapshot",
)
async def get_dataset_manifest(
    snapshot_id: UUID,
    service: Annotated[DatasetService, Depends(get_dataset_service)],
) -> dict[str, Any]:
    try:
        return await service.get_published_manifest(snapshot_id)
    except DatasetNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset snapshot not found.",
        ) from None
    except Exception:
        logger.exception("Failed to load dataset manifest snapshot_id=%s", snapshot_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Dataset registry is temporarily unavailable.",
        ) from None


@router.get(
    "/{snapshot_id}/candles",
    response_model=CandlePageResponse,
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
        status.HTTP_409_CONFLICT: {"model": ErrorResponse},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"model": ErrorResponse},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ErrorResponse},
    },
    summary="Query verified candles for one published partition",
)
async def get_dataset_candles(
    snapshot_id: UUID,
    service: Annotated[CandleQueryService, Depends(get_candle_query_service)],
    symbol: Annotated[str, Query(min_length=1)],
    timeframe: Annotated[str, Query(min_length=1)],
    start: Annotated[datetime | None, Query()] = None,
    end: Annotated[datetime | None, Query()] = None,
    after: Annotated[datetime | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_CANDLE_LIMIT)] = DEFAULT_CANDLE_LIMIT,
) -> CandlePageResponse:
    try:
        query = build_candle_query(
            snapshot_id=snapshot_id,
            symbol=symbol,
            timeframe=timeframe,
            start=start,
            end=end,
            after=after,
            limit=limit,
        )
        page = await service.query(query)
    except CandleQueryValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from None
    except DatasetNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset snapshot not found.",
        ) from None
    except CandlePartitionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candle partition not found.",
        ) from None
    except UnsupportedCandleDatasetError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Dataset candle schema is unsupported for querying.",
        ) from None
    except (DatasetIntegrityError, CandlePartitionIntegrityError):
        logger.exception("Candle integrity failure snapshot_id=%s", snapshot_id)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Dataset integrity verification failed.",
        ) from None
    except Exception:
        logger.exception("Failed to query candles snapshot_id=%s", snapshot_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Candle query is temporarily unavailable.",
        ) from None
    return candle_page_to_response(page)
