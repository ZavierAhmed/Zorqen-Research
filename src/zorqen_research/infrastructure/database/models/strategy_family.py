"""Strategy-family ORM model (metadata registry only)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from zorqen_research.infrastructure.database.base import Base


class StrategyFamilyModel(Base):
    """Persisted strategy-family registry row."""

    __tablename__ = "strategy_families"
    __table_args__ = (
        CheckConstraint(
            "research_priority IN ('primary', 'secondary')",
            name="research_priority_allowed",
        ),
        CheckConstraint(
            "status IN ('active', 'inactive')",
            name="status_allowed",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    code: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    research_priority: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
