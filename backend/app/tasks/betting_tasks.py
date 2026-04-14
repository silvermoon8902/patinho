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
    from app.services.voting_service import start_voting

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
                        await start_voting(db, bet.id)
                        locked_count += 1
                        logger.info("Started voting for bet %s", bet.id)
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
