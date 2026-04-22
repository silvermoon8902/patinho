"""Champion palpite (tournament-wide champion prediction per user)

Revision ID: 012
Revises: 011
Create Date: 2026-04-22
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tournament_champion_palpites",
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
        sa.Column("predicted_champion", sa.String(100), nullable=False),
        sa.Column("points_earned", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "bet_id", "user_id", name="uq_champion_palpite_bet_user"
        ),
    )

    # Seed the WC 2026 Bolão template
    op.execute(
        """
        INSERT INTO bet_templates (code, name, description, sport, kind, scoring_rules, prize_distribution, event_selector, palpite_schema, is_active)
        VALUES (
            'bolao_copa_mundo_2026',
            'Bolão da Copa do Mundo 2026',
            'Palpite em todos os jogos da Copa do Mundo FIFA 2026. Pontuação dobrada nas eliminatórias. Palpite no campeão vale 30 pontos extras.',
            'football',
            'tournament',
            '{
                "group_stage": {"winner": 3, "exact_score": 6},
                "knockout":    {"winner": 6, "exact_score": 12},
                "champion":    30
            }'::jsonb,
            'winner_takes_all_split_tied',
            '{"tournament_id": "fifa-wc-2026", "api_league_id": 1, "api_season": 2026}'::jsonb,
            '{"fields": ["home_score", "away_score", "champion"], "lock_minutes_before_kickoff": 10}'::jsonb,
            true
        )
        ON CONFLICT (code) DO NOTHING;
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM bet_templates WHERE code = 'bolao_copa_mundo_2026';")
    op.drop_table("tournament_champion_palpites")
