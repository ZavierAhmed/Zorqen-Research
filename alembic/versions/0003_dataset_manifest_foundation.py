"""Create dataset snapshot and partition tables.

Revision ID: 0003_dataset_manifest_foundation
Revises: 0002_core_registry_and_audit
Create Date: 2026-08-03

This migration intentionally does not import application model code.
It does not seed fixture dataset rows.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_dataset_manifest_foundation"
down_revision: str | None = "0002_core_registry_and_audit"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "dataset_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("exchange", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("manifest_version", sa.String(length=32), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=True),
        sa.Column("total_rows", sa.BigInteger(), nullable=False),
        sa.Column("minimum_open_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("maximum_open_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "validation_summary",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'published', 'rejected')",
            name=op.f("ck_dataset_snapshots_status_allowed"),
        ),
        sa.CheckConstraint(
            "total_rows >= 0",
            name=op.f("ck_dataset_snapshots_total_rows_non_negative"),
        ),
        sa.CheckConstraint(
            "(status <> 'published') OR (content_hash IS NOT NULL AND published_at IS NOT NULL)",
            name=op.f("ck_dataset_snapshots_published_requires_hash_and_timestamp"),
        ),
        sa.CheckConstraint(
            "exchange IN ('binance_futures')",
            name=op.f("ck_dataset_snapshots_exchange_allowed"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_dataset_snapshots")),
        sa.UniqueConstraint("name", name=op.f("uq_dataset_snapshots_name")),
    )

    op.create_table(
        "dataset_partitions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dataset_snapshot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("timeframe", sa.String(length=16), nullable=False),
        sa.Column("artifact_key", sa.String(length=128), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("byte_size", sa.BigInteger(), nullable=False),
        sa.Column("row_count", sa.BigInteger(), nullable=False),
        sa.Column("minimum_open_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("maximum_open_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "row_count >= 0",
            name=op.f("ck_dataset_partitions_row_count_non_negative"),
        ),
        sa.CheckConstraint(
            "byte_size >= 0",
            name=op.f("ck_dataset_partitions_byte_size_non_negative"),
        ),
        sa.CheckConstraint(
            "symbol IN ('BTCUSDT', 'ETHUSDT', 'BNBUSDT')",
            name=op.f("ck_dataset_partitions_symbol_allowed"),
        ),
        sa.CheckConstraint(
            "timeframe IN ('1m', '3m', '5m', '15m', '30m', '1h', '4h', '1d', '1w')",
            name=op.f("ck_dataset_partitions_timeframe_allowed"),
        ),
        sa.ForeignKeyConstraint(
            ["dataset_snapshot_id"],
            ["dataset_snapshots.id"],
            name=op.f("fk_dataset_partitions_dataset_snapshot_id_dataset_snapshots"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_dataset_partitions")),
        sa.UniqueConstraint(
            "dataset_snapshot_id",
            "symbol",
            "timeframe",
            name=op.f("uq_dataset_partitions_snapshot_symbol_timeframe"),
        ),
        sa.UniqueConstraint(
            "dataset_snapshot_id",
            "artifact_key",
            name=op.f("uq_dataset_partitions_snapshot_artifact_key"),
        ),
    )
    op.create_index(
        "ix_dataset_partitions_dataset_snapshot_id",
        "dataset_partitions",
        ["dataset_snapshot_id"],
        unique=False,
    )
    op.create_index(
        "ix_dataset_partitions_symbol_timeframe",
        "dataset_partitions",
        ["symbol", "timeframe"],
        unique=False,
    )
    op.create_index(
        "ix_dataset_partitions_open_time_range",
        "dataset_partitions",
        ["minimum_open_time", "maximum_open_time"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_dataset_partitions_open_time_range", table_name="dataset_partitions")
    op.drop_index("ix_dataset_partitions_symbol_timeframe", table_name="dataset_partitions")
    op.drop_index("ix_dataset_partitions_dataset_snapshot_id", table_name="dataset_partitions")
    op.drop_table("dataset_partitions")
    op.drop_table("dataset_snapshots")
