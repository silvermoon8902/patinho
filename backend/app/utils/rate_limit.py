"""
Per-user Redis rate limit helper.

Used to protect endpoints that nginx's per-IP zones can't fence well
because legitimate users on the same WiFi share an IP and abusers can
rotate IPs while the user account stays the same. Fails open when Redis
is unreachable so an infra outage doesn't block legitimate use.
"""
from __future__ import annotations

import logging
from uuid import UUID

from fastapi import HTTPException, status

from app.config import settings

logger = logging.getLogger(__name__)


async def enforce_user_rate_limit(
    user_id: UUID,
    bucket: str,
    limit: int,
    window_seconds: int,
    detail: str = "Muitas requisições. Tente novamente em alguns minutos.",
) -> None:
    """Increment a sliding counter and reject when above `limit`.

    Each bucket is a fixed-window counter — simple and predictable. The
    first request in a window sets the TTL; subsequent ones inherit it.
    Failing open on Redis errors is intentional (availability > absolute
    rate-limit guarantee).
    """
    try:
        import redis.asyncio as aioredis

        client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        key = f"rl:{bucket}:{user_id}"
        count = await client.incr(key)
        if count == 1:
            await client.expire(key, window_seconds)
        if count > limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=detail,
            )
    except HTTPException:
        raise
    except Exception:
        logger.warning(
            "rate_limit: Redis unavailable for bucket %s, failing open", bucket
        )
