"""Compliance/LGPD fields on users

Revision ID: 007
Revises: 006
Create Date: 2026-04-21

Adds:
  - accepted_terms_at / terms_version: records when the user accepted ToS
  - age_acknowledged_at: explicit 18+ acknowledgement
  - self_excluded_at: user-initiated self-exclusion timestamp (non-null = opted out)
  - monthly_deposit_cap: optional cap user sets on themselves
  - monthly_participation_cap: optional cap on total bet entries per month

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("accepted_terms_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("terms_version", sa.String(20), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("age_acknowledged_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("self_excluded_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("monthly_deposit_cap", sa.Numeric(12, 2), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("monthly_participation_cap", sa.Numeric(12, 2), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "monthly_participation_cap")
    op.drop_column("users", "monthly_deposit_cap")
    op.drop_column("users", "self_excluded_at")
    op.drop_column("users", "age_acknowledged_at")
    op.drop_column("users", "terms_version")
    op.drop_column("users", "accepted_terms_at")
