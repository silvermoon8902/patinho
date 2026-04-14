import logging
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.badge import Badge, UserBadge
from app.models.bet import Bet
from app.models.participation import Participation

logger = logging.getLogger(__name__)

BADGE_DEFINITIONS = [
    {
        "name": "Primeiro Passo",
        "description": "Participou da primeira aposta",
        "icon": "PP",
        "category": "participation",
    },
    {
        "name": "Apostador Serial",
        "description": "Participou de 10 apostas",
        "icon": "AS",
        "category": "participation",
    },
    {
        "name": "Criador",
        "description": "Criou a primeira aposta",
        "icon": "CR",
        "category": "creation",
    },
    {
        "name": "Vencedor",
        "description": "Venceu a primeira aposta",
        "icon": "VE",
        "category": "victory",
    },
    {
        "name": "Mao Quente",
        "description": "Venceu 5 apostas",
        "icon": "MQ",
        "category": "victory",
    },
    {
        "name": "Invicto",
        "description": "3 vitorias consecutivas",
        "icon": "IN",
        "category": "streak",
    },
    {
        "name": "Social",
        "description": "Convidou 5 amigos que entraram na plataforma",
        "icon": "SO",
        "category": "social",
    },
    {
        "name": "Pote de Ouro",
        "description": "Ganhou R$100+ em uma unica aposta",
        "icon": "PO",
        "category": "prize",
    },
]

CATEGORY_COLORS = {
    "participation": "#4F46E5",
    "creation": "#0891B2",
    "victory": "#D97706",
    "streak": "#DC2626",
    "social": "#059669",
    "prize": "#7C3AED",
}


async def seed_badges(db: AsyncSession) -> None:
    """Create initial badge definitions if they don't exist."""
    for badge_def in BADGE_DEFINITIONS:
        result = await db.execute(
            select(Badge).where(Badge.name == badge_def["name"])
        )
        if not result.scalar_one_or_none():
            db.add(Badge(**badge_def))

    await db.flush()
    logger.info("Badge definitions seeded")


async def get_user_badges(db: AsyncSession, user_id: UUID) -> list[dict]:
    """List user's earned badges with full badge info."""
    # Get all badges
    result = await db.execute(select(Badge))
    all_badges = list(result.scalars().all())

    # Get user's earned badge IDs
    result = await db.execute(
        select(UserBadge).where(UserBadge.user_id == user_id)
    )
    earned = {ub.badge_id: ub.awarded_at for ub in result.scalars().all()}

    badges = []
    for badge in all_badges:
        badges.append(
            {
                "id": str(badge.id),
                "name": badge.name,
                "description": badge.description,
                "icon": badge.icon,
                "category": badge.category,
                "earned": badge.id in earned,
                "awarded_at": (
                    earned[badge.id].isoformat() if badge.id in earned else None
                ),
            }
        )

    return badges


async def _has_badge(db: AsyncSession, user_id: UUID, badge_name: str) -> bool:
    result = await db.execute(
        select(UserBadge)
        .join(Badge)
        .where(UserBadge.user_id == user_id, Badge.name == badge_name)
    )
    return result.scalar_one_or_none() is not None


async def _award_badge(db: AsyncSession, user_id: UUID, badge_name: str) -> bool:
    """Award a badge if not already earned. Returns True if newly awarded."""
    if await _has_badge(db, user_id, badge_name):
        return False

    result = await db.execute(select(Badge).where(Badge.name == badge_name))
    badge = result.scalar_one_or_none()
    if not badge:
        logger.warning("Badge %s not found in DB", badge_name)
        return False

    db.add(UserBadge(user_id=user_id, badge_id=badge.id))
    await db.flush()
    logger.info("Awarded badge '%s' to user %s", badge_name, user_id)
    return True


async def check_and_award_badges(db: AsyncSession, user_id: UUID) -> list[str]:
    """Check all badge criteria and award any new ones. Returns list of newly awarded badge names."""
    awarded: list[str] = []

    # Count participations
    result = await db.execute(
        select(func.count()).select_from(Participation).where(
            Participation.user_id == user_id
        )
    )
    participation_count = result.scalar() or 0

    # Primeiro Passo — first bet joined
    if participation_count >= 1:
        if await _award_badge(db, user_id, "Primeiro Passo"):
            awarded.append("Primeiro Passo")

    # Apostador Serial — 10 bets joined
    if participation_count >= 10:
        if await _award_badge(db, user_id, "Apostador Serial"):
            awarded.append("Apostador Serial")

    # Criador — first bet created
    result = await db.execute(
        select(func.count()).select_from(Bet).where(Bet.creator_id == user_id)
    )
    created_count = result.scalar() or 0
    if created_count >= 1:
        if await _award_badge(db, user_id, "Criador"):
            awarded.append("Criador")

    # Count wins (participations with prize_amount > 0)
    result = await db.execute(
        select(func.count()).select_from(Participation).where(
            Participation.user_id == user_id,
            Participation.prize_amount > 0,
        )
    )
    win_count = result.scalar() or 0

    # Vencedor — first bet won
    if win_count >= 1:
        if await _award_badge(db, user_id, "Vencedor"):
            awarded.append("Vencedor")

    # Mao Quente — 5 bets won
    if win_count >= 5:
        if await _award_badge(db, user_id, "Mao Quente"):
            awarded.append("Mao Quente")

    # Invicto — 3 consecutive wins
    result = await db.execute(
        select(Participation)
        .where(Participation.user_id == user_id)
        .order_by(Participation.created_at.desc())
        .limit(20)
    )
    recent = list(result.scalars().all())

    consecutive = 0
    max_consecutive = 0
    for p in recent:
        if p.prize_amount is not None and p.prize_amount > 0:
            consecutive += 1
            max_consecutive = max(max_consecutive, consecutive)
        else:
            if p.prize_amount is not None:
                consecutive = 0

    if max_consecutive >= 3:
        if await _award_badge(db, user_id, "Invicto"):
            awarded.append("Invicto")

    # Pote de Ouro — won R$100+ in a single bet
    result = await db.execute(
        select(func.max(Participation.prize_amount)).where(
            Participation.user_id == user_id,
            Participation.prize_amount is not None,
        )
    )
    max_prize = result.scalar()
    if max_prize is not None and max_prize >= Decimal("100"):
        if await _award_badge(db, user_id, "Pote de Ouro"):
            awarded.append("Pote de Ouro")

    # Social — invited 5 friends who joined
    # Check if User model has invited_by or referral fields
    # For now skip if no referral tracking exists yet
    # This will be enabled once referral system is connected

    return awarded
