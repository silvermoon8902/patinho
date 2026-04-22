from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TournamentBet(Base):
    """Links a bet to its template + tracks tournament phase progress."""

    __tablename__ = "tournament_bets"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    bet_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("bets.id", ondelete="CASCADE"), unique=True, index=True
    )
    template_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("bet_templates.id"))
    tournament_id: Mapped[str] = mapped_column(String(50), index=True)
    current_phase: Mapped[str] = mapped_column(String(30), default="group")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class TournamentPalpite(Base):
    """Per-user per-fixture palpite within a tournament bet."""

    __tablename__ = "tournament_palpites"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    bet_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("bets.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    fixture_id: Mapped[str] = mapped_column(String(50), index=True)
    phase: Mapped[str] = mapped_column(String(30))
    predicted_home_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    predicted_away_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    predicted_winner: Mapped[str | None] = mapped_column(String(30), nullable=True)
    points_earned: Mapped[int] = mapped_column(Integer, default=0)
    locks_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "bet_id", "user_id", "fixture_id", name="uq_palpite_bet_user_fixture"
        ),
    )


class TournamentChampionPalpite(Base):
    """Champion prediction for a tournament (one per user per bet)."""

    __tablename__ = "tournament_champion_palpites"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    bet_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("bets.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    predicted_champion: Mapped[str] = mapped_column(String(100))
    points_earned: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "bet_id", "user_id", name="uq_champion_palpite_bet_user"
        ),
    )
