"""
Invite-link shortener.

WhatsApp's anti-phishing refuses to auto-linkify raw IPv4 URLs over plain
HTTP (e.g. http://187.127.25.239/invite/abc), so the message arrives as
plain text. While the deployment is on a bare IP, we proxy through
TinyURL to get an HTTPS short URL that WhatsApp DOES linkify. (is.gd was
the first choice but blocks IP-host shortening as anti-abuse.)

Once the app moves to a real HTTPS domain this endpoint becomes redundant
and can be retired (or kept as a vanity shortener).
"""
from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.bet import Bet
from app.models.user import User
from app.services.auth_service import get_current_active_user
from sqlalchemy import select

logger = logging.getLogger(__name__)

router = APIRouter(tags=["share"])

_redis_client: Redis | None = None


async def _get_redis() -> Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client


async def _shorten(long_url: str) -> str | None:
    """Call TinyURL's free shortener (no auth needed). ~150ms typical."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                "https://tinyurl.com/api-create.php",
                params={"url": long_url},
            )
        if resp.status_code != 200:
            logger.warning(
                "tinyurl shorten failed: %s %s", resp.status_code, resp.text[:80]
            )
            return None
        text = (resp.text or "").strip()
        if not text.startswith("https://tinyurl.com/"):
            logger.warning("tinyurl returned unexpected body: %s", text[:120])
            return None
        return text
    except Exception:
        logger.exception("tinyurl shorten exception")
        return None


def _public_origin(request: Request) -> str:
    """Best public-facing origin for invite URLs.

    Prefers the explicit APP_URL setting, falls back to the request's
    forwarded host so the shortener still works when the env var is
    unset on the VPS.
    """
    cfg = (settings.APP_URL or "").rstrip("/")
    if cfg and not cfg.startswith("http://localhost"):
        return cfg
    forwarded_host = request.headers.get("x-forwarded-host") or request.headers.get("host")
    forwarded_proto = request.headers.get("x-forwarded-proto") or "http"
    if forwarded_host:
        return f"{forwarded_proto}://{forwarded_host}"
    return cfg or "http://localhost:5173"


@router.get("/bets/invite/{invite_token}/short-url")
async def get_invite_short_url(
    invite_token: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    from app.utils.rate_limit import enforce_user_rate_limit

    # Cap how often a single user can ask us to mint short URLs. Cached
    # hits are unaffected because the cache check happens after this
    # gate; the gate itself just prevents flooding TinyURL.
    await enforce_user_rate_limit(
        user.id,
        bucket="share_short_url",
        limit=60,
        window_seconds=3600,
        detail="Muitas requisições de compartilhamento. Aguarde alguns minutos.",
    )
    """Return an HTTPS short URL for the given bet invite.

    Cached per invite_token for 30 days (is.gd links don't expire).
    Authenticated only — the token is sensitive enough to not want it in
    plain logs of an unauthenticated handler.
    """
    bet = (
        await db.execute(select(Bet).where(Bet.invite_token == invite_token))
    ).scalar_one_or_none()
    if not bet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Convite não encontrado"
        )

    redis = await _get_redis()
    cache_key = f"shorturl:invite:{invite_token}"
    cached = await redis.get(cache_key)
    if cached:
        return {"short_url": cached, "cached": True}

    long_url = f"{_public_origin(request)}/invite/{invite_token}"
    short = await _shorten(long_url)
    if not short:
        return {"short_url": long_url, "cached": False, "fallback": True}

    await redis.set(cache_key, short, ex=60 * 60 * 24 * 30)
    return {"short_url": short, "cached": False}
