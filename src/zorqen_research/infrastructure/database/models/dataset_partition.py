"""Dataset partition ORM model."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from zorqen_research.infrastructure.database.base import Base
from zorqen_research.infrastructure.database.models.dataset_snapshot import DatasetSnapshotModel


class DatasetPartitionModel(Base):
    """Persisted immutable partition referencing an artifact."""

    __tablename__ = "dataset_partitions"
    __table_args__ = (
        UniqueConstraint(
            "dataset_snapshot_id",
            "symbol",
            "timeframe",
            name="uq_dataset_partitions_snapshot_symbol_timeframe",
        ),
        UniqueConstraint(
            "dataset_snapshot_id",
            "artifact_key",
            name="uq_dataset_partitions_snapshot_artifact_key",
        ),
        CheckConstraint("row_count >= 0", name="row_count_non_negative"),
        CheckConstraint("byte_size >= 0", name="byte_size_non_negative"),
        CheckConstraint(
            "symbol IN ('BTCUSDT', 'ETHUSDT', 'BNBUSDT')",
            name="symbol_allowed",
        ),
        CheckConstraint(
            "timeframe IN ('1m', '3m', '5m', '15m', '30m', '1h', '4h', '1d', '1w')",
            name="timeframe_allowed",
        ),
        Index("ix_dataset_partitions_dataset_snapshot_id", "dataset_snapshot_id"),
        Index("ix_dataset_partitions_symbol_timeframe", "symbol", "timeframe"),
        Index(
            "ix_dataset_partitions_open_time_range",
            "minimum_open_time",
            "maximum_open_time",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dataset_snapshots.id", ondelete="CASCADE"),
        nullable=False,
    )
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(16), nullable=False)
    artifact_key: Mapped[str] = mapped_column(String(128), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    byte_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    row_count: Mapped[int] = mapped_column(BigInteger, nullable=False)
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

    snapshot: Mapped[DatasetSnapshotModel] = relationship(
        "DatasetSnapshotModel",
        back_populates="partitions",
    )
