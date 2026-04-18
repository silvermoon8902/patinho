"""Single entry amount, declared winner flow, contestation

Revision ID: 003
Revises: 002
Create Date: 2026-04-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new enum value for pending_confirmation status
    op.execute("ALTER TYPE betstatus ADD VALUE IF NOT EXISTS 'pending_confirmation' BEFORE 'voting'")

    # Add entry_amount column (defaults to min_entry value from existing rows)
    op.add_column("bets", sa.Column("entry_amount", sa.Numeric(12, 2), nullable=True))
    op.execute("UPDATE bets SET entry_amount = min_entry")
    op.alter_column("bets", "entry_amount", nullable=False, server_default="5")

    # Add declared_winner fields
    op.add_column(
        "bets",
        sa.Column("declared_winner_option_id", UUID(as_uuid=True), sa.ForeignKey("bet_options.id"), nullable=True),
    )
    op.add_column("bets", sa.Column("declared_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("bets", sa.Column("confirmation_closes_at", sa.DateTime(timezone=True), nullable=True))

    # Update participation constraint: amount must equal bet entry_amount
    # We keep the >= 5 AND <= 1000 check as a safety net
    # (actual enforcement is in the service layer using bet.entry_amount)

    # Drop old min_entry/max_entry constraints and columns (keep data in entry_amount)
    op.drop_column("bets", "min_entry")
    op.drop_column("bets", "max_entry")

    # Contestations table: tracks who contested a declared winner
    op.create_table(
        "contestations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("bet_id", UUID(as_uuid=True), sa.ForeignKey("bets.id"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("bet_id", "user_id", name="uq_contestation_bet_user"),
    )


def downgrade() -> None:
    op.drop_table("contestations")

    op.add_column("bets", sa.Column("min_entry", sa.Numeric(12, 2), nullable=False, server_default="5"))
    op.add_column("bets", sa.Column("max_entry", sa.Numeric(12, 2), nullable=False, server_default="1000"))
    op.execute("UPDATE bets SET min_entry = entry_amount, max_entry = entry_amount")

    op.drop_column("bets", "confirmation_closes_at")
    op.drop_column("bets", "declared_at")
    op.drop_column("bets", "declared_winner_option_id")
    op.drop_column("bets", "entry_amount")

    # Note: cannot remove enum value in postgres easily; leave pending_confirmation
