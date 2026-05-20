"""
Shareable invite links.

WhatsApp's anti-phishing refuses to auto-linkify raw IPv4 URLs (e.g.
http://187.127.25.239/invite/abc) — they arrive as plain text. The fix is
to hand out a URL with a real *hostname*: PUBLIC_BASE_URL points at a
sslip.io wildcard-DNS name (187-127-25-239.sslip.io) that resolves to the
same IP. WhatsApp linkifies it because it ends in a real TLD.

No third-party shortener is involved — earlier we proxied through TinyURL
but it started showing a "preview" interstitial for IP-backed links.
Once a real domain is purchased, just point PUBLIC_BASE_URL at it.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.bet import Bet
from app.models.user import User
from app.services.auth_service import get_current_active_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["share"])


def _public_origin(request: Request) -> str:
    """Public-facing origin for invite URLs.

    Order of preference:
      1. PUBLIC_BASE_URL (the sslip.io host, or the real domain later)
      2. APP_URL, if it's been set to something non-local
      3. the request's forwarded host (last-resort fallback)
    """
    base = (settings.PUBLIC_BASE_URL or "").rstrip("/")
    if base:
        return base
    cfg = (settings.APP_URL or "").rstrip("/")
    if cfg and not cfg.startswith("http://localhost"):
        return cfg
    forwarded_host = (
        request.headers.get("x-forwarded-host") or request.headers.get("host")
    )
    forwarded_proto = request.headers.get("x-forwarded-proto") or "http"
    if forwarded_host:
        return f"{forwarded_proto}://{forwarded_host}"
    return cfg or "http://localhost:5173"


@router.get("/leagues/{invite_code}/short-url")
async def get_league_short_url(
    invite_code: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    """Shareable join URL for a league (deep link that pre-fills the code)."""
    from app.models.league import League

    league = (
        await db.execute(select(League).where(League.invite_code == invite_code))
    ).scalar_one_or_none()
    if not league:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Liga não encontrada"
        )
    return {
        "short_url": f"{_public_origin(request)}/leagues/join/{invite_code}",
        "cached": False,
    }


@router.get("/bets/invite/{invite_token}/short-url")
async def get_invite_short_url(
    invite_token: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    """Shareable invite URL for a bet."""
    bet = (
        await db.execute(select(Bet).where(Bet.invite_token == invite_token))
    ).scalar_one_or_none()
    if not bet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Convite não encontrado"
        )
    return {
        "short_url": f"{_public_origin(request)}/invite/{invite_token}",
        "cached": False,
    }
