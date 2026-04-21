"""Add private leagues and league memberships

Revision ID: 006
Revises: 005
Create Date: 2026-04-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "leagues",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "owner_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "invite_code",
            sa.String(12),
            nullable=False,
            unique=True,
            index=True,
        ),
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
    )

    op.create_table(
        "league_memberships",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "league_id",
            UUID(as_uuid=True),
            sa.ForeignKey("leagues.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "league_id", "user_id", name="uq_league_membership_league_user"
        ),
    )

    op.add_column(
        "bets",
        sa.Column(
            "league_id",
            UUID(as_uuid=True),
            sa.ForeignKey("leagues.id"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_bets_league_id",
        "bets",
        ["league_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_bets_league_id", table_name="bets")
    op.drop_column("bets", "league_id")
    op.drop_table("league_memberships")
    op.drop_table("leagues")
