"""Bet template registry

Revision ID: 009
Revises: 008
Create Date: 2026-04-22

Registers named bet templates (Bolão da Copa, Vencedor da partida, etc.) with
their scoring rules, prize distribution, and palpite schema. Extensible: new
templates can be added without schema changes.

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID


revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "bet_templates",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("code", sa.String(50), nullable=False, unique=True, index=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("sport", sa.String(30), nullable=False),
        sa.Column("kind", sa.String(30), nullable=False, server_default="single_event"),
        # Scoring rules as JSON: { "group_stage": {"winner": 3, "exact": 6}, ... }
        sa.Column("scoring_rules", JSONB, nullable=False),
        sa.Column("prize_distribution", sa.String(30), nullable=False, server_default="winner_takes_all"),
        sa.Column("event_selector", JSONB, nullable=True),
        sa.Column("palpite_schema", JSONB, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("bet_templates")
