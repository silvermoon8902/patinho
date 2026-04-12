from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Participation(Base):
    __tablename__ = "participations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    bet_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("bets.id"))
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    bet_option_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("bet_options.id"))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    prize_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("bet_id", "user_id", name="uq_participation_bet_user"),
        CheckConstraint("amount <= 1000", name="ck_participation_max_amount"),
    )

    bet: Mapped["Bet"] = relationship(back_populates="participations")
    user: Mapped["User"] = relationship()
    bet_option: Mapped["BetOption"] = relationship(back_populates="participations")
