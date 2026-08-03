"""Empty baseline migration - infrastructure only, no domain tables.

Revision ID: 0001_baseline
Revises:
Create Date: 2026-08-03
"""

from __future__ import annotations

from collections.abc import Sequence

revision: str = "0001_baseline"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """No-op baseline. Domain schema belongs to later milestones."""
    pass


def downgrade() -> None:
    """No-op baseline downgrade."""
    pass
