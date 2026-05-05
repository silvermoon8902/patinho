from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class FunnelEvent(Base):
    """Lightweight per-user event log for funnel analytics.

    Designed to answer questions like "how many users register but never
    deposit", "how many open the invite but bounce before joining", etc.
    Kept intentionally minimal — replaces the need for a third-party
    analytics SDK while we're still pre-domain.
    """

    __tablename__ = "funnel_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    event: Mapped[str] = mapped_column(String(60), index=True)
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
