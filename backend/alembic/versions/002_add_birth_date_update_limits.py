"""Add birth_date to users, update bet/participation limits

Revision ID: 002
Revises: 001
Create Date: 2026-04-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add birth_date to users
    op.add_column("users", sa.Column("birth_date", sa.DateTime(), nullable=True))

    # Make phone NOT NULL (for existing rows, set empty string first)
    op.execute("UPDATE users SET phone = '' WHERE phone IS NULL")
    op.alter_column("users", "phone", nullable=False, server_default="")

    # Update participation min amount constraint
    op.drop_constraint("ck_participation_max_amount", "participations", type_="check")
    op.create_check_constraint(
        "ck_participation_amount_range",
        "participations",
        "amount >= 5 AND amount <= 1000",
    )

    # Update default fee to 8%
    op.execute(
        """
        UPDATE platform_config
        SET value = '{"fee_type": "percent", "fee_value": 8}', updated_at = NOW()
        WHERE key = 'default_fee'
        """
    )

    # Update bet min_entry default
    op.alter_column("bets", "min_entry", server_default="5")


def downgrade() -> None:
    op.alter_column("bets", "min_entry", server_default="1")

    op.execute(
        """
        UPDATE platform_config
        SET value = '{"fee_type": "percent", "fee_value": 10}', updated_at = NOW()
        WHERE key = 'default_fee'
        """
    )

    op.drop_constraint("ck_participation_amount_range", "participations", type_="check")
    op.create_check_constraint(
        "ck_participation_max_amount",
        "participations",
        "amount <= 1000",
    )

    op.alter_column("users", "phone", nullable=True, server_default=None)
    op.drop_column("users", "birth_date")
