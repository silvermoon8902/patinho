import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.bet import Bet, BetStatus
from app.models.bet_option import BetOption
from app.services.distribution_service import distribute_prizes

logger = logging.getLogger(__name__)


async def resolve_sports_bet(db: AsyncSession, bet_id: UUID) -> bool:
    """
    Resolve a sports bet using API-Football results.
    Called by Celery task when a match finishes.
    Returns True if resolved, False if not yet finished.
    """
    from app.integrations.api_football import api_football_client

    bet = await db.get(Bet, bet_id)
    if not bet:
        logger.warning("Bet %s not found for sports resolution", bet_id)
        return False

    if bet.status != BetStatus.LOCKED:
        logger.warning("Bet %s is not locked (status=%s), skipping", bet_id, bet.status)
        return False

    if not bet.sports_match_id:
        logger.warning("Bet %s has no sports_match_id", bet_id)
        return False

    fixture_result = await api_football_client.get_fixture_result(bet.sports_match_id)
    if fixture_result is None:
        # Match not finished yet
        return False

    # Load bet options
    result = await db.execute(
        select(BetOption).where(BetOption.bet_id == bet_id)
    )
    options = list(result.scalars().all())

    # Map fixture result to winning option
    # Convention: option labels match "Home", "Draw", "Away" or team names
    winner_label = fixture_result.get("winner")  # "Home", "Draw", "Away"
    winning_option = None

    if winner_label:
        # Try exact match first
        for opt in options:
            if opt.label.lower() == winner_label.lower():
                winning_option = opt
                break

        # Try partial match (e.g., team name in option label)
        if not winning_option:
            for opt in options:
                if winner_label.lower() in opt.label.lower():
                    winning_option = opt
                    break

    if not winning_option:
        logger.error(
            "Could not map winner '%s' to any option for bet %s. Options: %s",
            winner_label,
            bet_id,
            [o.label for o in options],
        )
        return False

    await distribute_prizes(db, bet_id, winning_option.id)
    logger.info("Resolved sports bet %s with winner option %s", bet_id, winning_option.id)
    return True


async def check_voting_consensus(db: AsyncSession, bet_id: UUID) -> bool:
    """
    Check if any option has >= 70% of total participant votes.
    If consensus reached, distribute prizes.
    Returns True if resolved.
    """
    from app.models.participation import Participation
    from app.models.vote import Vote

    bet = await db.get(Bet, bet_id)
    if not bet:
        return False

    if bet.status != BetStatus.VOTING:
        return False

    # Count total participants
    part_result = await db.execute(
        select(Participation).where(Participation.bet_id == bet_id)
    )
    participations = list(part_result.scalars().all())
    total_participants = len(participations)

    if total_participants == 0:
        return False

    # Count votes per option
    vote_result = await db.execute(
        select(Vote).where(Vote.bet_id == bet_id)
    )
    votes = list(vote_result.scalars().all())

    vote_counts: dict[UUID, int] = {}
    for vote in votes:
        vote_counts[vote.bet_option_id] = vote_counts.get(vote.bet_option_id, 0) + 1

    # Check if any option has >= 70% consensus
    threshold = 0.70
    for option_id, count in vote_counts.items():
        ratio = count / total_participants
        if ratio >= threshold:
            await distribute_prizes(db, bet_id, option_id)
            logger.info(
                "Voting consensus reached for bet %s: option %s with %.1f%%",
                bet_id,
                option_id,
                ratio * 100,
            )
            return True

    return False
