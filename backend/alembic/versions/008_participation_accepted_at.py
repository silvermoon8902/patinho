"""Add participations.accepted_at for tracking result acceptance

Revision ID: 008
Revises: 007
Create Date: 2026-04-22

Lets the bet resolve immediately when every non-creator participant has
accepted the declared result, instead of waiting the full 24h window.

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "participations",
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("participations", "accepted_at")
