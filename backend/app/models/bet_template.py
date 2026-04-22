from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class BetTemplate(Base):
    """
    Registered bet template (Bolão da Copa, Vencedor da partida, etc.).
    Configuration-driven so new templates can be added without schema changes.
    """

    __tablename__ = "bet_templates"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sport: Mapped[str] = mapped_column(String(30))
    kind: Mapped[str] = mapped_column(String(30), default="single_event")
    scoring_rules: Mapped[dict] = mapped_column(JSONB)
    prize_distribution: Mapped[str] = mapped_column(
        String(30), default="winner_takes_all"
    )
    event_selector: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    palpite_schema: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
