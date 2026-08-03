"""Core registry and audit persistence.

Revision ID: 0002_core_registry_and_audit
Revises: 0001_baseline
Create Date: 2026-08-03

Stable strategy-family seed UUIDs (documented in domain.strategy_families):
  adaptive_mtf_trend_breakout -> a1b2c3d4-e5f6-4789-a012-3456789abc01
  support_resistance          -> a1b2c3d4-e5f6-4789-a012-3456789abc02

This migration intentionally does not import application model code.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_core_registry_and_audit"
down_revision: str | None = "0001_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ADAPTIVE_MTF_ID = "a1b2c3d4-e5f6-4789-a012-3456789abc01"
SUPPORT_RESISTANCE_ID = "a1b2c3d4-e5f6-4789-a012-3456789abc02"


def upgrade() -> None:
    op.create_table(
        "strategy_families",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=128), nullable=False),
        sa.Column("display_name", sa.String(length=256), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("research_priority", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "research_priority IN ('primary', 'secondary')",
            name=op.f("ck_strategy_families_research_priority_allowed"),
        ),
        sa.CheckConstraint(
            "status IN ('active', 'inactive')",
            name=op.f("ck_strategy_families_status_allowed"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_strategy_families")),
        sa.UniqueConstraint("code", name=op.f("uq_strategy_families_code")),
    )

    op.create_table(
        "audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("actor_type", sa.String(length=64), nullable=False),
        sa.Column("actor_id", sa.String(length=128), nullable=True),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("entity_type", sa.String(length=128), nullable=False),
        sa.Column("entity_id", sa.String(length=128), nullable=True),
        sa.Column("correlation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_events")),
    )
    op.create_index(
        "ix_audit_events_occurred_at",
        "audit_events",
        ["occurred_at"],
        unique=False,
    )
    op.create_index(
        "ix_audit_events_entity_type_entity_id",
        "audit_events",
        ["entity_type", "entity_id"],
        unique=False,
    )
    op.create_index(
        "ix_audit_events_correlation_id",
        "audit_events",
        ["correlation_id"],
        unique=False,
    )

    strategy_families = sa.table(
        "strategy_families",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("code", sa.String()),
        sa.column("display_name", sa.String()),
        sa.column("description", sa.Text()),
        sa.column("research_priority", sa.String()),
        sa.column("status", sa.String()),
    )
    op.bulk_insert(
        strategy_families,
        [
            {
                "id": ADAPTIVE_MTF_ID,
                "code": "adaptive_mtf_trend_breakout",
                "display_name": "Adaptive Multi-Timeframe Trend Breakout",
                "description": (
                    "Primary initial research family for Zorqen Research. "
                    "Executable baseline behavior has not yet been defined in "
                    "Zorqen Research; this registry entry is metadata only."
                ),
                "research_priority": "primary",
                "status": "active",
            },
            {
                "id": SUPPORT_RESISTANCE_ID,
                "code": "support_resistance",
                "display_name": "Support and Resistance",
                "description": (
                    "Secondary initial research family for Zorqen Research. "
                    "Executable baseline behavior has not yet been defined; "
                    "this registry entry is metadata only."
                ),
                "research_priority": "secondary",
                "status": "active",
            },
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_audit_events_correlation_id", table_name="audit_events")
    op.drop_index("ix_audit_events_entity_type_entity_id", table_name="audit_events")
    op.drop_index("ix_audit_events_occurred_at", table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_table("strategy_families")
