import json
import logging
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.admin_fee import AdminFee
from app.models.bet import Bet, BetStatus
from app.models.bet_option import BetOption
from app.models.participation import Participation
from app.models.payment import Payment, PaymentStatus
from app.models.platform_config import PlatformConfig
from app.models.user import User
from app.services import distribution_service, wallet_service

logger = logging.getLogger(__name__)


async def get_dashboard_stats(db: AsyncSession) -> dict:
    """Return aggregated dashboard statistics."""
    total_users = await db.scalar(select(func.count(User.id)))
    total_bets = await db.scalar(select(func.count(Bet.id)))
    active_bets = await db.scalar(
        select(func.count(Bet.id)).where(
            Bet.status.in_([BetStatus.OPEN, BetStatus.LOCKED, BetStatus.VOTING])
        )
    )
    total_revenue = await db.scalar(
        select(func.coalesce(func.sum(AdminFee.amount), 0))
    )
    total_deposits = await db.scalar(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.status == PaymentStatus.APPROVED
        )
    )

    return {
        "total_users": total_users or 0,
        "total_bets": total_bets or 0,
        "active_bets": active_bets or 0,
        "total_revenue": float(total_revenue),
        "total_deposits": float(total_deposits),
    }


async def list_users(
    db: AsyncSession, skip: int = 0, limit: int = 20, search: str | None = None
) -> list[User]:
    """Paginated user list with optional search by email/username."""
    query = select(User).order_by(User.created_at.desc())

    if search:
        pattern = f"%{search}%"
        query = query.where(
            or_(
                User.email.ilike(pattern),
                User.username.ilike(pattern),
            )
        )

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def list_bets(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 20,
    status_filter: str | None = None,
) -> list[Bet]:
    """Paginated bet list with optional status filter."""
    query = (
        select(Bet)
        .options(selectinload(Bet.options), selectinload(Bet.participations))
        .order_by(Bet.created_at.desc())
    )

    if status_filter:
        try:
            bet_status = BetStatus(status_filter)
            query = query.where(Bet.status == bet_status)
        except ValueError:
            pass

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().unique().all())


async def toggle_user_active(
    db: AsyncSession, user_id: UUID, is_active: bool
) -> User:
    """Activate or deactivate a user."""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario nao encontrado",
        )

    user.is_active = is_active
    await db.flush()
    return user


async def make_admin(db: AsyncSession, user_id: UUID) -> User:
    """Promote a user to admin."""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario nao encontrado",
        )

    user.is_admin = True
    await db.flush()
    return user


async def get_fee_config(db: AsyncSession) -> dict:
    """Get current fee configuration."""
    result = await db.execute(
        select(PlatformConfig).where(PlatformConfig.key == "default_fee")
    )
    config = result.scalar_one_or_none()

    if config and config.value:
        return {
            "fee_type": config.value.get("fee_type", "percent"),
            "fee_value": float(config.value.get("fee_value", 8)),
        }

    return {"fee_type": "percent", "fee_value": 8.0}


async def update_fee_config(
    db: AsyncSession, fee_type: str, fee_value: float
) -> PlatformConfig:
    """Update the default fee (percent or fixed)."""
    if fee_type not in ("percent", "fixed"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="fee_type deve ser 'percent' ou 'fixed'",
        )

    if fee_value < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="fee_value deve ser maior ou igual a zero",
        )

    result = await db.execute(
        select(PlatformConfig).where(PlatformConfig.key == "default_fee")
    )
    config = result.scalar_one_or_none()

    new_value = {"fee_type": fee_type, "fee_value": fee_value}

    if config:
        config.value = new_value
    else:
        config = PlatformConfig(key="default_fee", value=new_value)
        db.add(config)

    await db.flush()
    return config


async def force_resolve_bet(
    db: AsyncSession, bet_id: UUID, winning_option_id: UUID
) -> Bet:
    """Admin force-resolves a bet by picking the winning option."""
    bet = await db.get(
        Bet,
        bet_id,
        options=[selectinload(Bet.options), selectinload(Bet.participations)],
    )
    if not bet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aposta nao encontrada",
        )

    if bet.status in (BetStatus.RESOLVED, BetStatus.CANCELLED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Aposta ja foi finalizada",
        )

    # Validate the winning option belongs to this bet
    option = await db.get(BetOption, winning_option_id)
    if not option or option.bet_id != bet_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Opcao invalida para esta aposta",
        )

    await distribution_service.distribute_prizes(db, bet_id, winning_option_id)
    await db.refresh(bet)
    return bet


async def force_cancel_bet(db: AsyncSession, bet_id: UUID) -> Bet:
    """Admin cancels a bet and refunds all participants."""
    bet = await db.get(
        Bet,
        bet_id,
        options=[selectinload(Bet.options), selectinload(Bet.participations)],
    )
    if not bet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aposta nao encontrada",
        )

    if bet.status in (BetStatus.RESOLVED, BetStatus.CANCELLED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Aposta ja foi finalizada",
        )

    # Refund all participants
    result = await db.execute(
        select(Participation).where(Participation.bet_id == bet_id)
    )
    participations = list(result.scalars().all())

    for p in participations:
        await wallet_service.unlock_funds(db, p.user_id, p.amount, bet_id)
        p.prize_amount = Decimal("0")

    bet.status = BetStatus.CANCELLED
    await db.flush()

    logger.info("Admin force-cancelled bet %s, refunded %d participants", bet_id, len(participations))
    return bet
