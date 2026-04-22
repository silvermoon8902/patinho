"""Rename admin_actions.metadata → action_metadata

Revision ID: 014
Revises: 013
Create Date: 2026-04-22

`metadata` is a reserved attribute on SQLAlchemy's DeclarativeBase. The
original migration (013) worked because the ORM mapping used an alias,
but autogen diffs would thrash on it. This migration makes the column
name match the Python attribute name exactly.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "014"
down_revision: Union[str, None] = "013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "admin_actions", "metadata", new_column_name="action_metadata"
    )


def downgrade() -> None:
    op.alter_column(
        "admin_actions", "action_metadata", new_column_name="metadata"
    )
