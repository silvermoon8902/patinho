"""Admin audit log + chat message moderation flag + account reactivation tracking

Revision ID: 013
Revises: 012
Create Date: 2026-04-22
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID


revision: str = "013"
down_revision: Union[str, None] = "012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "admin_actions",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "admin_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("action", sa.String(80), nullable=False, index=True),
        sa.Column(
            "target_user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column(
            "target_bet_id",
            UUID(as_uuid=True),
            sa.ForeignKey("bets.id"),
            nullable=True,
        ),
        sa.Column("metadata", JSONB, nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_admin_actions_created_at",
        "admin_actions",
        ["created_at"],
    )

    # Chat moderation: soft-delete flag per message.
    op.add_column(
        "chat_messages",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "chat_messages",
        sa.Column(
            "deleted_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("chat_messages", "deleted_by")
    op.drop_column("chat_messages", "deleted_at")
    op.drop_index("ix_admin_actions_created_at", table_name="admin_actions")
    op.drop_table("admin_actions")
