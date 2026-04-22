"""Tournament bet (links bet → template → tournament phase tracking)

Revision ID: 010
Revises: 009
Create Date: 2026-04-22
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tournament_bets",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "bet_id",
            UUID(as_uuid=True),
            sa.ForeignKey("bets.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
            index=True,
        ),
        sa.Column(
            "template_id",
            UUID(as_uuid=True),
            sa.ForeignKey("bet_templates.id"),
            nullable=False,
        ),
        sa.Column("tournament_id", sa.String(50), nullable=False, index=True),
        sa.Column(
            "current_phase",
            sa.String(30),
            nullable=False,
            server_default="group",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("tournament_bets")
