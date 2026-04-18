from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class BetOption(Base):
    __tablename__ = "bet_options"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    bet_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("bets.id"))
    label: Mapped[str] = mapped_column(String(200))
    is_winner: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    bet: Mapped["Bet"] = relationship(back_populates="options", foreign_keys=[bet_id])
    participations: Mapped[list["Participation"]] = relationship(
        back_populates="bet_option"
    )
