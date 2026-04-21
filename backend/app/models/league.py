from __future__ import annotations

import secrets
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _generate_invite_code() -> str:
    # token_urlsafe(8) → 11 chars base64url, safely under 12.
    return secrets.token_urlsafe(8)[:12]


class League(Base):
    __tablename__ = "leagues"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(80))
    description: Mapped[str | None] = mapped_column(Text)
    invite_code: Mapped[str] = mapped_column(
        String(12), unique=True, index=True, default=_generate_invite_code
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    memberships: Mapped[list["LeagueMembership"]] = relationship(
        back_populates="league",
        cascade="all, delete-orphan",
    )
    owner: Mapped["User"] = relationship(foreign_keys=[owner_id])
