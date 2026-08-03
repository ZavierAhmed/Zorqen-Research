"""Dataset snapshot ORM model."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import BigInteger, CheckConstraint, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from zorqen_research.infrastructure.database.base import Base

if TYPE_CHECKING:
    from zorqen_research.infrastructure.database.models.dataset_partition import (
        DatasetPartitionModel,
    )


class DatasetSnapshotModel(Base):
    """Persisted dataset snapshot metadata."""

    __tablename__ = "dataset_snapshots"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'published', 'rejected')",
            name="status_allowed",
        ),
        CheckConstraint("total_rows >= 0", name="total_rows_non_negative"),
        CheckConstraint(
            "(status <> 'published') OR (content_hash IS NOT NULL AND published_at IS NOT NULL)",
            name="published_requires_hash_and_timestamp",
        ),
        CheckConstraint(
            "exchange IN ('binance_futures')",
            name="exchange_allowed",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(256), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    exchange: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    manifest_version: Mapped[str] = mapped_column(String(32), nullable=False)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    total_rows: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    minimum_open_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    maximum_open_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    validation_summary: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    partitions: Mapped[list[DatasetPartitionModel]] = relationship(
        "DatasetPartitionModel",
        back_populates="snapshot",
        cascade="all, delete-orphan",
        order_by="DatasetPartitionModel.symbol, DatasetPartitionModel.timeframe",
    )
