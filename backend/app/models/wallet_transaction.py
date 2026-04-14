from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TransactionType(str, enum.Enum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    BET_LOCK = "bet_lock"
    BET_UNLOCK = "bet_unlock"
    PRIZE_CREDIT = "prize_credit"
    FEE_DEBIT = "fee_debit"
    REFUND = "refund"


class WalletTransaction(Base):
    __tablename__ = "wallet_transactions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    wallet_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("wallets.id"))
    type: Mapped[TransactionType] = mapped_column(
        Enum(TransactionType, name="transactiontype", values_callable=lambda x: [e.value for e in x])
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    balance_before: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    balance_after: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    reference_id: Mapped[uuid.UUID | None] = mapped_column()
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    wallet: Mapped["Wallet"] = relationship(back_populates="transactions")
