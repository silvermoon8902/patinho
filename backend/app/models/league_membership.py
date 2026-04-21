from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class LeagueMembership(Base):
    __tablename__ = "league_memberships"
    __table_args__ = (
        UniqueConstraint(
            "league_id", "user_id", name="uq_league_membership_league_user"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    league_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("leagues.id", ondelete="CASCADE")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    league: Mapped["League"] = relationship(back_populates="memberships")
    user: Mapped["User"] = relationship(foreign_keys=[user_id])
