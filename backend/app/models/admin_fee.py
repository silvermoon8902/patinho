from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class FeeType(str, enum.Enum):
    PERCENT = "percent"
    FIXED = "fixed"


class AdminFee(Base):
    __tablename__ = "admin_fees"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    bet_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("bets.id"), unique=True
    )
    fee_type: Mapped[FeeType] = mapped_column(
        Enum(FeeType, name="feetype", values_callable=lambda x: [e.value for e in x])
    )
    fee_value: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    prize_pool_snapshot: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    bet: Mapped["Bet"] = relationship()
