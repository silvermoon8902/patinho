from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Vote(Base):
    __tablename__ = "votes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    bet_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("bets.id"))
    voter_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    bet_option_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("bet_options.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("bet_id", "voter_id", name="uq_vote_bet_voter"),
    )

    bet: Mapped["Bet"] = relationship()
    voter: Mapped["User"] = relationship()
    bet_option: Mapped["BetOption"] = relationship()
