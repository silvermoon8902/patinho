import asyncio
import logging
from datetime import datetime, timezone

from app.celery_app import celery_app

logger = logging.getLogger(__name__)


async def _lock_expired_bets_async() -> int:
    """
    Find open bets past closes_at.
    For auto_api: set status=locked.
    For voting: start voting phase.
    """
    from sqlalchemy import select

    from app.database import async_session_maker
    from app.models.bet import Bet, BetStatus, ResolutionType

    async with async_session_maker() as db:
        try:
            now = datetime.now(timezone.utc)

            result = await db.execute(
                select(Bet).where(
                    Bet.status == BetStatus.OPEN,
                    Bet.closes_at <= now,
                )
            )
            bets = list(result.scalars().all())

            if not bets:
                logger.debug("No expired open bets to lock")
                return 0

            logger.info("Locking %d expired open bets", len(bets))
            locked_count = 0

            for bet in bets:
                try:
                    if bet.resolution_type == ResolutionType.AUTO_API:
                        bet.status = BetStatus.LOCKED
                        locked_count += 1
                        logger.info("Locked sports bet %s", bet.id)
                    elif bet.resolution_type == ResolutionType.VOTING:
                        # Creator-declared-winner flow: lock first.
                        # Creator then calls declare-winner endpoint.
                        bet.status = BetStatus.LOCKED
                        locked_count += 1
                        logger.info(
                            "Locked voting bet %s awaiting creator declaration",
                            bet.id,
                        )
                except Exception:
                    logger.exception("Error locking/transitioning bet %s", bet.id)
                    continue

            await db.commit()
            logger.info("Processed %d/%d expired bets", locked_count, len(bets))
            return locked_count
        except Exception:
            await db.rollback()
            logger.exception("Error in lock_expired_bets task")
            raise


@celery_app.task(name="app.tasks.betting.lock_expired_bets")
def lock_expired_bets() -> int:
    """Celery beat task: lock expired open bets or start voting."""
    return asyncio.run(_lock_expired_bets_async())


# Voting bets that the creator never declares should not trap participant
# funds forever. After this many days in LOCKED with no declared winner
# we cancel the bet and refund every participant (creator included).
STALE_LOCK_REFUND_DAYS = 7


async def _refund_stale_locked_bets_async() -> int:
    """Auto-cancel + refund voting bets stuck in LOCKED for too long.

    Safety net for the case where the bet creator disappears, gets sick,
    or simply forgets to declare the winner — without this, participant
    funds stay frozen indefinitely. No admin fee is charged.
    """
    from datetime import timedelta

    from sqlalchemy import select

    from app.database import async_session_maker
    from app.models.bet import Bet, BetStatus, ResolutionType
    from app.services import dispute_service

    cutoff = datetime.now(timezone.utc) - timedelta(days=STALE_LOCK_REFUND_DAYS)
    refunded = 0
    async with async_session_maker() as db:
        try:
            rows = (
                await db.execute(
                    select(Bet).where(
                        Bet.status == BetStatus.LOCKED,
                        Bet.resolution_type == ResolutionType.VOTING,
                        Bet.declared_winner_option_id.is_(None),
                        Bet.closes_at <= cutoff,
                    )
                )
            ).scalars().all()
            for bet in rows:
                try:
                    await dispute_service.refund_all(db, bet.id)
                    refunded += 1
                    logger.warning(
                        "Auto-cancelled stale locked bet %s "
                        "(creator never declared after %d days)",
                        bet.id, STALE_LOCK_REFUND_DAYS,
                    )
                except Exception:
                    logger.exception(
                        "Error auto-cancelling stale locked bet %s", bet.id
                    )
                    continue
            await db.commit()
        except Exception:
            await db.rollback()
            logger.exception("Error in refund_stale_locked_bets task")
            raise
    return refunded


@celery_app.task(name="app.tasks.betting.refund_stale_locked_bets")
def refund_stale_locked_bets() -> int:
    """Celery beat task: refund participants of stale locked voting bets."""
    return asyncio.run(_refund_stale_locked_bets_async())
