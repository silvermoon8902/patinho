"""Helper to record admin actions to the audit log."""
from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin_action import AdminAction


def _client_ip(request: Request | None) -> str | None:
    if request is None:
        return None
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else None


async def record(
    db: AsyncSession,
    *,
    admin_id: UUID,
    action: str,
    target_user_id: UUID | None = None,
    target_bet_id: UUID | None = None,
    metadata: dict[str, Any] | None = None,
    request: Request | None = None,
) -> None:
    """Append a single audit row. Never raises — audit must not break flows."""
    try:
        row = AdminAction(
            admin_id=admin_id,
            action=action,
            target_user_id=target_user_id,
            target_bet_id=target_bet_id,
            action_metadata=metadata,
            ip_address=_client_ip(request),
        )
        db.add(row)
        await db.flush()
    except Exception:
        # Intentionally swallow — audit failures should never block the caller.
        pass
