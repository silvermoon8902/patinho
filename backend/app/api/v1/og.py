"""
Open Graph preview endpoints.

Generates a per-invite SVG preview that WhatsApp / Facebook / Twitter
can unfurl. SVG keeps this dependency-free (no PIL / Pillow required);
social sites that require raster can hit the browser's svg-to-png path
or we can swap this to Pillow later.
"""
from __future__ import annotations

import html
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.bet import Bet

router = APIRouter(tags=["og"])


def _format_brl(v) -> str:
    try:
        return f"R$ {float(v):.2f}".replace(".", ",")
    except Exception:
        return "R$ 0,00"


def _fit_text(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"


@router.get("/og/invite/{invite_token}")
async def invite_og_image(
    invite_token: str,
    db: AsyncSession = Depends(get_db),
):
    """Return an SVG (1200x630) describing the bet for social unfurls."""
    result = await db.execute(
        select(Bet).where(Bet.invite_token == invite_token)
    )
    bet = result.scalar_one_or_none()
    if not bet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bet not found",
        )

    title = html.escape(_fit_text(bet.title or "Patinho", 60))
    entry = html.escape(_format_brl(bet.entry_amount))
    desc_raw = (bet.description or "Desafio entre amigos no Patinho").strip()
    desc = html.escape(_fit_text(desc_raw, 120))

    svg = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#001F3F"/>
      <stop offset="100%" stop-color="#002e5d"/>
    </linearGradient>
  </defs>
  <rect width="1200" height="630" fill="url(#bg)"/>
  <rect x="60" y="60" width="1080" height="510" rx="32" fill="#ffffff" fill-opacity="0.04" stroke="#FFD10D" stroke-opacity="0.2" stroke-width="2"/>
  <text x="100" y="160" font-family="Poppins, Arial, sans-serif" font-size="40" font-weight="700" fill="#FFD10D">Patinho</text>
  <text x="100" y="200" font-family="Poppins, Arial, sans-serif" font-size="22" font-weight="400" fill="#ffffff" fill-opacity="0.7">Desafios entre amigos</text>
  <text x="100" y="320" font-family="Poppins, Arial, sans-serif" font-size="56" font-weight="700" fill="#ffffff">
    <tspan>{title}</tspan>
  </text>
  <text x="100" y="400" font-family="Poppins, Arial, sans-serif" font-size="26" font-weight="400" fill="#ffffff" fill-opacity="0.8">
    <tspan>{desc}</tspan>
  </text>
  <g transform="translate(100, 470)">
    <rect width="360" height="72" rx="36" fill="#FFD10D"/>
    <text x="34" y="46" font-family="Poppins, Arial, sans-serif" font-size="24" font-weight="700" fill="#001F3F">Entrada</text>
    <text x="180" y="46" font-family="Poppins, Arial, sans-serif" font-size="30" font-weight="700" fill="#001F3F">{entry}</text>
  </g>
  <text x="1100" y="560" text-anchor="end" font-family="Poppins, Arial, sans-serif" font-size="22" font-weight="600" fill="#ffffff" fill-opacity="0.6">patinho.app</text>
</svg>"""

    return Response(
        content=svg,
        media_type="image/svg+xml",
        headers={"Cache-Control": "public, max-age=3600"},
    )
