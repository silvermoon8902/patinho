import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bet import Bet, BetStatus
from app.models.bet_option import BetOption
from app.models.contestation import Contestation
from app.models.participation import Participation

logger = logging.getLogger(__name__)

CONFIRMATION_WINDOW_HOURS = 24


async def declare_winner(
    db: AsyncSession,
    bet_id: UUID,
    creator_id: UUID,
    winning_option_id: UUID,
) -> Bet:
    """Creator declares the winning option. Moves bet to PENDING_CONFIRMATION."""
    bet = await db.get(Bet, bet_id)
    if not bet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bet not found",
        )

    if bet.creator_id != creator_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the bet creator can declare the winner",
        )

    if bet.status != BetStatus.LOCKED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bet must be locked to declare a winner",
        )

    option = await db.get(BetOption, winning_option_id)
    if not option or option.bet_id != bet_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid winning option for this bet",
        )

    now = datetime.now(timezone.utc)
    bet.declared_winner_option_id = winning_option_id
    bet.declared_at = now
    bet.confirmation_closes_at = now + timedelta(hours=CONFIRMATION_WINDOW_HOURS)
    bet.status = BetStatus.PENDING_CONFIRMATION

    await db.flush()
    logger.info(
        "Creator %s declared option %s as winner for bet %s",
        creator_id,
        winning_option_id,
        bet_id,
    )
    return bet


async def _ensure_participant(
    db: AsyncSession, bet_id: UUID, user_id: UUID
) -> Participation:
    result = await db.execute(
        select(Participation).where(
            Participation.bet_id == bet_id,
            Participation.user_id == user_id,
        )
    )
    participation = result.scalar_one_or_none()
    if not participation:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only participants can perform this action",
        )
    return participation


async def contest_result(
    db: AsyncSession,
    bet_id: UUID,
    user_id: UUID,
    reason: str | None,
) -> Contestation:
    """Participant contests the declared winner. Triggers voting if at least one contestation."""
    bet = await db.get(Bet, bet_id)
    if not bet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bet not found",
        )

    if bet.status != BetStatus.PENDING_CONFIRMATION:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bet is not pending confirmation",
        )

    now = datetime.now(timezone.utc)
    if bet.confirmation_closes_at and bet.confirmation_closes_at <= now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmation window has expired",
        )

    await _ensure_participant(db, bet_id, user_id)

    contestation = Contestation(
        bet_id=bet_id,
        user_id=user_id,
        reason=reason,
    )
    db.add(contestation)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already contested this bet",
        )

    # Count contestations
    count_result = await db.execute(
        select(func.count())
        .select_from(Contestation)
        .where(Contestation.bet_id == bet_id)
    )
    count = count_result.scalar() or 0

    # If >=1 contestation, move to voting
    if count >= 1:
        bet.status = BetStatus.VOTING
        await db.flush()
        logger.info(
            "Bet %s moved to VOTING after %d contestation(s)", bet_id, count
        )

    return contestation


async def accept_result(
    db: AsyncSession, bet_id: UUID, user_id: UUID
) -> None:
    """Participant accepts the declared result. No-op for UI feedback.

    The auto-resolve task handles final distribution after the 24h window.
    """
    bet = await db.get(Bet, bet_id)
    if not bet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bet not found",
        )

    if bet.status != BetStatus.PENDING_CONFIRMATION:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bet is not pending confirmation",
        )

    await _ensure_participant(db, bet_id, user_id)
    logger.info("User %s accepted result for bet %s", user_id, bet_id)
    return None


async def get_contestations(
    db: AsyncSession, bet_id: UUID
) -> list[Contestation]:
    """List contestations for a bet."""
    result = await db.execute(
        select(Contestation)
        .where(Contestation.bet_id == bet_id)
        .order_by(Contestation.created_at.asc())
    )
    return list(result.scalars().all())
