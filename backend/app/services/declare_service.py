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
) -> dict:
    """
    Participant accepts the declared result.

    Records the acceptance timestamp on their participation row. If every
    non-creator participant has accepted, the bet resolves immediately
    and prizes are distributed — no need to wait for the 24h window.

    The auto-resolve task still handles the fallback where some
    participants never respond before the window closes.

    Returns a status dict so the UI can distinguish "recorded" from
    "resolved now".
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

    participation = await _ensure_participant(db, bet_id, user_id)

    now = datetime.now(timezone.utc)
    if participation.accepted_at is None:
        participation.accepted_at = now
        await db.flush()
        logger.info("User %s accepted result for bet %s", user_id, bet_id)

    # Count outstanding non-creator participations
    result = await db.execute(
        select(Participation).where(
            Participation.bet_id == bet_id,
            Participation.user_id != bet.creator_id,
        )
    )
    non_creator_parts = list(result.scalars().all())
    total = len(non_creator_parts)
    accepted = sum(1 for p in non_creator_parts if p.accepted_at is not None)

    if total == 0 or accepted >= total:
        # Unanimous (or creator-only bet) — resolve immediately
        from app.services.distribution_service import distribute_prizes

        if bet.declared_winner_option_id is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Winner option missing at resolution",
            )
        await distribute_prizes(db, bet_id, bet.declared_winner_option_id)
        logger.info(
            "Bet %s resolved immediately after unanimous acceptance (%d/%d)",
            bet_id, accepted, total,
        )
        return {
            "detail": "Result accepted — bet resolved and prize distributed",
            "resolved": True,
            "acceptances": accepted,
            "total_participants": total,
        }

    return {
        "detail": "Result accepted. Waiting for the other participants.",
        "resolved": False,
        "acceptances": accepted,
        "total_participants": total,
    }


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
