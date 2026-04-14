import asyncio
import logging
from datetime import datetime, timedelta, timezone

from app.celery_app import celery_app

logger = logging.getLogger(__name__)

# Voting window: 24 hours after bet closes
VOTING_WINDOW_HOURS = 24


async def _check_voting_consensus_async() -> int:
    """
    Find bets with status='voting'. Check consensus for each.
    Start dispute if voting window expired without consensus.
    """
    from sqlalchemy import select

    from app.database import async_session_maker
    from app.models.bet import Bet, BetStatus, ResolutionType
    from app.services.dispute_service import start_dispute
    from app.services.resolution_service import check_voting_consensus

    async with async_session_maker() as db:
        try:
            result = await db.execute(
                select(Bet).where(
                    Bet.status == BetStatus.VOTING,
                    Bet.resolution_type == ResolutionType.VOTING,
                )
            )
            bets = list(result.scalars().all())

            if not bets:
                logger.debug("No voting bets to check")
                return 0

            logger.info("Checking %d voting bets for consensus", len(bets))
            resolved_count = 0
            now = datetime.now(timezone.utc)

            for bet in bets:
                try:
                    consensus_reached = await check_voting_consensus(db, bet.id)
                    if consensus_reached:
                        resolved_count += 1
                    else:
                        # Check if voting window expired
                        voting_deadline = bet.closes_at + timedelta(hours=VOTING_WINDOW_HOURS)
                        if now >= voting_deadline:
                            await start_dispute(db, bet.id)
                            logger.info(
                                "Voting expired for bet %s, starting dispute",
                                bet.id,
                            )
                except Exception:
                    logger.exception("Error checking consensus for bet %s", bet.id)
                    continue

            await db.commit()
            logger.info("Resolved %d/%d voting bets", resolved_count, len(bets))
            return resolved_count
        except Exception:
            await db.rollback()
            logger.exception("Error in check_voting_consensus_all task")
            raise


async def _check_expired_disputes_async() -> int:
    """Find disputed bets older than 48h. Refund all participants."""
    from sqlalchemy import select

    from app.database import async_session_maker
    from app.models.bet import Bet, BetStatus
    from app.services.dispute_service import refund_all

    async with async_session_maker() as db:
        try:
            now = datetime.now(timezone.utc)
            cutoff = now - timedelta(hours=48)

            result = await db.execute(
                select(Bet).where(
                    Bet.status == BetStatus.DISPUTED,
                    Bet.updated_at <= cutoff,
                )
            )
            bets = list(result.scalars().all())

            if not bets:
                logger.debug("No expired disputes to process")
                return 0

            logger.info("Processing %d expired disputes", len(bets))
            refunded_count = 0

            for bet in bets:
                try:
                    await refund_all(db, bet.id)
                    refunded_count += 1
                except Exception:
                    logger.exception("Error refunding bet %s", bet.id)
                    continue

            await db.commit()
            logger.info("Refunded %d/%d expired disputes", refunded_count, len(bets))
            return refunded_count
        except Exception:
            await db.rollback()
            logger.exception("Error in check_expired_disputes task")
            raise


@celery_app.task(name="app.tasks.voting.check_voting_consensus_all")
def check_voting_consensus_all() -> int:
    """Celery beat task: check voting consensus and start disputes."""
    return asyncio.run(_check_voting_consensus_async())


@celery_app.task(name="app.tasks.disputes.check_expired_disputes")
def check_expired_disputes() -> int:
    """Celery beat task: refund expired disputes (48h)."""
    return asyncio.run(_check_expired_disputes_async())
