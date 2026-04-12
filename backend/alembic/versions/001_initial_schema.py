"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-04-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON, UUID, ENUM

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Create enums via raw SQL (idempotent) ---
    op.execute("DO $$ BEGIN CREATE TYPE transactiontype AS ENUM ('deposit','withdrawal','bet_lock','bet_unlock','prize_credit','fee_debit','refund'); EXCEPTION WHEN duplicate_object THEN NULL; END $$")
    op.execute("DO $$ BEGIN CREATE TYPE paymentstatus AS ENUM ('pending','approved','rejected','cancelled','expired'); EXCEPTION WHEN duplicate_object THEN NULL; END $$")
    op.execute("DO $$ BEGIN CREATE TYPE resolutiontype AS ENUM ('auto_api','voting'); EXCEPTION WHEN duplicate_object THEN NULL; END $$")
    op.execute("DO $$ BEGIN CREATE TYPE betstatus AS ENUM ('draft','open','locked','voting','disputed','resolved','cancelled'); EXCEPTION WHEN duplicate_object THEN NULL; END $$")
    op.execute("DO $$ BEGIN CREATE TYPE feetype AS ENUM ('percent','fixed'); EXCEPTION WHEN duplicate_object THEN NULL; END $$")

    # Reference existing enums (create_type=False prevents DDL re-creation)
    transactiontype_enum = ENUM('deposit','withdrawal','bet_lock','bet_unlock','prize_credit','fee_debit','refund', name='transactiontype', create_type=False)
    paymentstatus_enum = ENUM('pending','approved','rejected','cancelled','expired', name='paymentstatus', create_type=False)
    resolutiontype_enum = ENUM('auto_api','voting', name='resolutiontype', create_type=False)
    betstatus_enum = ENUM('draft','open','locked','voting','disputed','resolved','cancelled', name='betstatus', create_type=False)
    feetype_enum = ENUM('percent','fixed', name='feetype', create_type=False)

    # --- users ---
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.String(255), nullable=False, unique=True, index=True),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("cpf", sa.String(14), nullable=True),
        sa.Column("username", sa.String(50), nullable=False, unique=True, index=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("total_points", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # --- wallets ---
    op.create_table(
        "wallets",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, unique=True),
        sa.Column("balance", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("locked_balance", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("balance >= 0", name="ck_wallet_balance_positive"),
    )

    # --- wallet_transactions ---
    op.create_table(
        "wallet_transactions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("wallet_id", UUID(as_uuid=True), sa.ForeignKey("wallets.id"), nullable=False),
        sa.Column("type", transactiontype_enum, nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("balance_before", sa.Numeric(12, 2), nullable=False),
        sa.Column("balance_after", sa.Numeric(12, 2), nullable=False),
        sa.Column("reference_id", UUID(as_uuid=True), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # --- payments ---
    op.create_table(
        "payments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("status", paymentstatus_enum, nullable=False, server_default="pending"),
        sa.Column("mp_payment_id", sa.String(100), nullable=True),
        sa.Column("mp_external_reference", sa.String(100), nullable=True, unique=True),
        sa.Column("pix_qr_code", sa.Text(), nullable=True),
        sa.Column("pix_copy_paste", sa.Text(), nullable=True),
        sa.Column("webhook_payload", JSON, nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # --- bets ---
    op.create_table(
        "bets",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("creator_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("invite_token", sa.String(32), nullable=False, unique=True, index=True),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("resolution_type", resolutiontype_enum, nullable=False),
        sa.Column("status", betstatus_enum, nullable=False, server_default="open"),
        sa.Column("min_entry", sa.Numeric(12, 2), nullable=False, server_default="1"),
        sa.Column("max_entry", sa.Numeric(12, 2), nullable=False, server_default="1000"),
        sa.Column("max_participants", sa.Integer(), nullable=False, server_default=sa.text("100")),
        sa.Column("sports_match_id", sa.String(100), nullable=True),
        sa.Column("mediator_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("closes_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("chat_closes_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # --- bet_options ---
    op.create_table(
        "bet_options",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("bet_id", UUID(as_uuid=True), sa.ForeignKey("bets.id"), nullable=False),
        sa.Column("label", sa.String(200), nullable=False),
        sa.Column("is_winner", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # --- participations ---
    op.create_table(
        "participations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("bet_id", UUID(as_uuid=True), sa.ForeignKey("bets.id"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("bet_option_id", UUID(as_uuid=True), sa.ForeignKey("bet_options.id"), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("prize_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("bet_id", "user_id", name="uq_participation_bet_user"),
        sa.CheckConstraint("amount <= 1000", name="ck_participation_max_amount"),
    )

    # --- votes ---
    op.create_table(
        "votes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("bet_id", UUID(as_uuid=True), sa.ForeignKey("bets.id"), nullable=False),
        sa.Column("voter_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("bet_option_id", UUID(as_uuid=True), sa.ForeignKey("bet_options.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("bet_id", "voter_id", name="uq_vote_bet_voter"),
    )

    # --- dispute_evidence ---
    op.create_table(
        "dispute_evidence",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("bet_id", UUID(as_uuid=True), sa.ForeignKey("bets.id"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("image_url", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # --- chat_messages ---
    op.create_table(
        "chat_messages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("bet_id", UUID(as_uuid=True), sa.ForeignKey("bets.id"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("content", sa.String(1000), nullable=False),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "char_length(content) >= 1 AND char_length(content) <= 1000",
            name="ck_chat_message_content_length",
        ),
    )

    # --- badges ---
    op.create_table(
        "badges",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("icon", sa.String(50), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # --- user_badges ---
    op.create_table(
        "user_badges",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("badge_id", UUID(as_uuid=True), sa.ForeignKey("badges.id"), nullable=False),
        sa.Column("awarded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "badge_id", name="uq_user_badge"),
    )

    # --- admin_fees ---
    op.create_table(
        "admin_fees",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("bet_id", UUID(as_uuid=True), sa.ForeignKey("bets.id"), nullable=False, unique=True),
        sa.Column("fee_type", feetype_enum, nullable=False),
        sa.Column("fee_value", sa.Numeric(12, 2), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("prize_pool_snapshot", sa.Numeric(12, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # --- platform_config ---
    op.create_table(
        "platform_config",
        sa.Column("key", sa.String(100), primary_key=True),
        sa.Column("value", JSON, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # --- Seed default platform config ---
    op.execute(
        """
        INSERT INTO platform_config (key, value, updated_at)
        VALUES ('default_fee', '{"fee_type": "percent", "fee_value": 10}', NOW())
        """
    )


def downgrade() -> None:
    op.drop_table("platform_config")
    op.drop_table("admin_fees")
    op.drop_table("user_badges")
    op.drop_table("badges")
    op.drop_table("chat_messages")
    op.drop_table("dispute_evidence")
    op.drop_table("votes")
    op.drop_table("participations")
    op.drop_table("bet_options")
    op.drop_table("bets")
    op.drop_table("payments")
    op.drop_table("wallet_transactions")
    op.drop_table("wallets")
    op.drop_table("users")

    op.execute("DROP TYPE IF EXISTS feetype")
    op.execute("DROP TYPE IF EXISTS betstatus")
    op.execute("DROP TYPE IF EXISTS resolutiontype")
    op.execute("DROP TYPE IF EXISTS paymentstatus")
    op.execute("DROP TYPE IF EXISTS transactiontype")
