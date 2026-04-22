"""Per-user per-fixture palpites for tournament bets

Revision ID: 011
Revises: 010
Create Date: 2026-04-22
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tournament_palpites",
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
            index=True,
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("fixture_id", sa.String(50), nullable=False, index=True),
        sa.Column("phase", sa.String(30), nullable=False),
        sa.Column("predicted_home_score", sa.Integer, nullable=True),
        sa.Column("predicted_away_score", sa.Integer, nullable=True),
        sa.Column("predicted_winner", sa.String(30), nullable=True),
        sa.Column("points_earned", sa.Integer, nullable=False, server_default="0"),
        sa.Column("locks_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "bet_id", "user_id", "fixture_id", name="uq_palpite_bet_user_fixture"
        ),
    )


def downgrade() -> None:
    op.drop_table("tournament_palpites")
