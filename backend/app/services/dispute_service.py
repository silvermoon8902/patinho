import logging
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bet import Bet, BetStatus
from app.models.dispute_evidence import DisputeEvidence
from app.models.participation import Participation
from app.services import wallet_service
from app.services.distribution_service import distribute_prizes

logger = logging.getLogger(__name__)


async def submit_evidence(
    db: AsyncSession,
    user_id: UUID,
    bet_id: UUID,
    text: str,
    image_url: str | None = None,
) -> DisputeEvidence:
    """Submit evidence for a disputed bet. User must be a participant."""
    bet = await db.get(Bet, bet_id)
    if not bet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bet not found",
        )

    if bet.status != BetStatus.DISPUTED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bet is not in disputed status",
        )

    # Check user is a participant
    result = await db.execute(
        select(Participation).where(
            Participation.bet_id == bet_id,
            Participation.user_id == user_id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only participants can submit evidence",
        )

    evidence = DisputeEvidence(
        bet_id=bet_id,
        user_id=user_id,
        text=text,
        image_url=image_url,
    )
    db.add(evidence)
    await db.flush()

    logger.info("Evidence submitted for bet %s by user %s", bet_id, user_id)
    return evidence


async def resolve_dispute(
    db: AsyncSession,
    mediator_id: UUID,
    bet_id: UUID,
    winning_option_id: UUID,
) -> None:
    """Resolve a disputed bet. Only the creator or designated mediator can resolve."""
    bet = await db.get(Bet, bet_id)
    if not bet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bet not found",
        )

    if bet.status != BetStatus.DISPUTED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bet is not in disputed status",
        )

    # Check mediator authorization
    is_creator = bet.creator_id == mediator_id
    is_mediator = bet.mediator_user_id is not None and bet.mediator_user_id == mediator_id
    if not is_creator and not is_mediator:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the bet creator or designated mediator can resolve disputes",
        )

    await distribute_prizes(db, bet_id, winning_option_id)
    logger.info("Dispute resolved for bet %s by mediator %s", bet_id, mediator_id)


async def start_dispute(db: AsyncSession, bet_id: UUID) -> None:
    """Set bet status to disputed. Called when voting doesn't reach 70% consensus."""
    bet = await db.get(Bet, bet_id)
    if not bet:
        logger.warning("Bet %s not found for start_dispute", bet_id)
        return

    bet.status = BetStatus.DISPUTED
    await db.flush()
    logger.info("Dispute started for bet %s", bet_id)


async def refund_all(db: AsyncSession, bet_id: UUID) -> None:
    """
    Refund all participants for an expired dispute (48h timeout).
    No admin fee is charged. Bet is cancelled.
    """
    bet = await db.get(Bet, bet_id)
    if not bet:
        logger.warning("Bet %s not found for refund_all", bet_id)
        return

    result = await db.execute(
        select(Participation).where(Participation.bet_id == bet_id)
    )
    participations = list(result.scalars().all())

    for p in participations:
        await wallet_service.unlock_funds(db, p.user_id, p.amount, bet_id)
        p.prize_amount = Decimal("0")

    bet.status = BetStatus.CANCELLED
    await db.flush()

    logger.info("Refunded all %d participants for bet %s", len(participations), bet_id)
