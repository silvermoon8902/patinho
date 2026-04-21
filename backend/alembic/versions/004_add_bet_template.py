"""Add template column to bets

Revision ID: 004
Revises: 003
Create Date: 2026-04-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "bets",
        sa.Column("template", sa.String(50), nullable=True),
    )
    # Backfill existing sport bets (auto_api resolution) as match_winner,
    # which was the only template prior to this migration.
    op.execute(
        "UPDATE bets SET template = 'match_winner' WHERE resolution_type = 'auto_api'"
    )


def downgrade() -> None:
    op.drop_column("bets", "template")
