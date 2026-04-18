from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ResolutionType(str, enum.Enum):
    AUTO_API = "auto_api"
    VOTING = "voting"


class BetStatus(str, enum.Enum):
    DRAFT = "draft"
    OPEN = "open"
    LOCKED = "locked"
    PENDING_CONFIRMATION = "pending_confirmation"
    VOTING = "voting"
    DISPUTED = "disputed"
    RESOLVED = "resolved"
    CANCELLED = "cancelled"


class Bet(Base):
    __tablename__ = "bets"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    creator_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    invite_token: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    category: Mapped[str] = mapped_column(String(50))
    resolution_type: Mapped[ResolutionType] = mapped_column(
        Enum(ResolutionType, name="resolutiontype", values_callable=lambda x: [e.value for e in x])
    )
    status: Mapped[BetStatus] = mapped_column(
        Enum(BetStatus, name="betstatus", values_callable=lambda x: [e.value for e in x]),
        default=BetStatus.OPEN,
    )
    entry_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=5, server_default="5"
    )
    max_participants: Mapped[int] = mapped_column(default=100)
    sports_match_id: Mapped[str | None] = mapped_column(String(100))
    mediator_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id")
    )
    declared_winner_option_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("bet_options.id")
    )
    declared_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confirmation_closes_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closes_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    chat_closes_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    options: Mapped[list["BetOption"]] = relationship(back_populates="bet")
    participations: Mapped[list["Participation"]] = relationship(
        back_populates="bet"
    )
    creator: Mapped["User"] = relationship(foreign_keys=[creator_id])
