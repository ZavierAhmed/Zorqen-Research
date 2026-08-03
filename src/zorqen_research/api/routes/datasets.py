"""Read-only dataset API routes."""

from __future__ import annotations

import logging
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from zorqen_research.api.dependencies import get_db_session
from zorqen_research.api.schemas.datasets import (
    DatasetListResponse,
    DatasetSnapshotDetailResponse,
    ErrorResponse,
    snapshot_to_detail,
    snapshot_to_summary,
)
from zorqen_research.application.datasets.service import (
    DatasetNotFoundError,
    DatasetService,
)
from zorqen_research.core.config import Settings
from zorqen_research.infrastructure.artifacts.local import LocalFilesystemArtifactStore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/datasets", tags=["datasets"])


def get_dataset_service(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DatasetService:
    settings: Settings = request.app.state.settings
    store = LocalFilesystemArtifactStore(settings.artifact_root_configured)
    return DatasetService(session, store)


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
