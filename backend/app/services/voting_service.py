import logging
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bet import Bet, BetStatus
from app.models.bet_option import BetOption
from app.models.participation import Participation
from app.models.vote import Vote

logger = logging.getLogger(__name__)


async def cast_vote(
    db: AsyncSession, user_id: UUID, bet_id: UUID, option_id: UUID
) -> Vote:
    """Cast a vote for a bet option. User must be a participant."""
    bet = await db.get(Bet, bet_id)
    if not bet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bet not found",
        )

    if bet.status != BetStatus.VOTING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bet is not in voting phase",
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
            detail="Only participants can vote",
        )

    # Check user hasn't voted already
    result = await db.execute(
        select(Vote).where(
            Vote.bet_id == bet_id,
            Vote.voter_id == user_id,
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already voted on this bet",
        )

    # Validate option belongs to this bet
    option = await db.get(BetOption, option_id)
    if not option or option.bet_id != bet_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid option for this bet",
        )

    vote = Vote(
        bet_id=bet_id,
        voter_id=user_id,
        bet_option_id=option_id,
    )
    db.add(vote)
    await db.flush()

    logger.info("User %s voted for option %s on bet %s", user_id, option_id, bet_id)

    # Evaluate consensus right after each vote — resolves immediately
    # once supermajority or full-turnout majority is reached.
    from app.services.resolution_service import check_voting_consensus
    try:
        await check_voting_consensus(db, bet_id)
    except Exception:
        logger.exception("Error checking consensus after vote on bet %s", bet_id)

    return vote


async def get_vote_counts(db: AsyncSession, bet_id: UUID) -> dict[UUID, int]:
    """Return vote counts per option for display."""
    result = await db.execute(
        select(Vote.bet_option_id, func.count().label("count"))
        .where(Vote.bet_id == bet_id)
        .group_by(Vote.bet_option_id)
    )
    return {row.bet_option_id: row.count for row in result.all()}


async def start_voting(db: AsyncSession, bet_id: UUID) -> None:
    """Set bet status to voting. Called when closes_at expires for voting-type bets."""
    bet = await db.get(Bet, bet_id)
    if not bet:
        logger.warning("Bet %s not found for start_voting", bet_id)
        return

    if bet.status != BetStatus.OPEN:
        logger.warning(
            "Bet %s is not open (status=%s), cannot start voting", bet_id, bet.status
        )
        return

    bet.status = BetStatus.VOTING
    await db.flush()
    logger.info("Voting started for bet %s", bet_id)
