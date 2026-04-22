"""
Open Graph preview endpoints.

Generates a per-invite social preview. Two variants:
  - /og/invite/{token}.svg — dependency-free SVG
  - /og/invite/{token}.png — rendered via Pillow for WhatsApp/FB unfurl
    (most social crawlers prefer raster)

The no-extension `/og/invite/{token}` path returns SVG for backward
compatibility with the initial release.
"""
from __future__ import annotations

import html
import io
import logging

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.bet import Bet

logger = logging.getLogger(__name__)
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


def _render_png(title: str, description: str, entry: str) -> bytes:
    """Render a 1200x630 PNG social card with Pillow. Mirrors the SVG layout."""
    from PIL import Image, ImageDraw, ImageFont

    W, H = 1200, 630
    NAVY = (0, 31, 63, 255)
    NAVY_LIGHT = (0, 46, 93, 255)
    YELLOW = (255, 209, 13, 255)
    WHITE = (255, 255, 255, 255)

    img = Image.new("RGBA", (W, H), NAVY)
    draw = ImageDraw.Draw(img)
    # Soft diagonal gradient
    for y in range(H):
        mix = y / H
        r = int(NAVY[0] + (NAVY_LIGHT[0] - NAVY[0]) * mix)
        g = int(NAVY[1] + (NAVY_LIGHT[1] - NAVY[1]) * mix)
        b = int(NAVY[2] + (NAVY_LIGHT[2] - NAVY[2]) * mix)
        draw.line((0, y, W, y), fill=(r, g, b, 255))

    # Card border
    draw.rounded_rectangle(
        (60, 60, W - 60, H - 60),
        radius=32,
        outline=(255, 209, 13, 50),
        width=2,
    )

    font_candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
    ]
    def pick(size: int):
        for c in font_candidates:
            try:
                return ImageFont.truetype(c, size)
            except Exception:
                continue
        return ImageFont.load_default()

    f_brand = pick(48)
    f_tag = pick(22)
    f_title = pick(64)
    f_desc = pick(28)
    f_pill = pick(30)

    draw.text((100, 140), "Patinho", fill=YELLOW, font=f_brand)
    draw.text((100, 200), "Desafios entre Amigos", fill=(255, 255, 255, 180), font=f_tag)

    # Title (wrap if long)
    max_chars = 28
    lines = []
    cur = ""
    for word in title.split():
        probe = (cur + " " + word).strip()
        if len(probe) > max_chars and cur:
            lines.append(cur)
            cur = word
        else:
            cur = probe
    if cur:
        lines.append(cur)
    y = 270
    for line in lines[:2]:
        draw.text((100, y), line, fill=WHITE, font=f_title)
        y += 76

    # Description
    draw.text((100, max(y + 10, 410)), description[:90], fill=(255, 255, 255, 200), font=f_desc)

    # Entry pill
    pill_x, pill_y, pill_w, pill_h = 100, 500, 380, 72
    draw.rounded_rectangle(
        (pill_x, pill_y, pill_x + pill_w, pill_y + pill_h),
        radius=36, fill=YELLOW,
    )
    draw.text((pill_x + 30, pill_y + 20), "Entrada", fill=NAVY, font=f_pill)
    draw.text((pill_x + 180, pill_y + 18), entry, fill=NAVY, font=f_pill)

    # URL footer
    draw.text((W - 260, H - 80), "patinho.app", fill=(255, 255, 255, 160), font=f_tag)

    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG", optimize=True)
    return buf.getvalue()


@router.get("/og/invite/{invite_token}.png")
async def invite_og_png(
    invite_token: str,
    db: AsyncSession = Depends(get_db),
):
    """PNG variant of the invite preview — preferred by most social unfurlers."""
    result = await db.execute(
        select(Bet).where(Bet.invite_token == invite_token)
    )
    bet = result.scalar_one_or_none()
    if not bet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bet not found",
        )

    title = _fit_text(bet.title or "Patinho", 80)
    entry = _format_brl(bet.entry_amount)
    desc = _fit_text((bet.description or "Desafio entre amigos no Patinho").strip(), 120)

    try:
        png = _render_png(title, desc, entry)
    except Exception:
        logger.exception("OG PNG render failed for bet %s", bet.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to render preview",
        )

    return Response(
        content=png,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=3600"},
    )
