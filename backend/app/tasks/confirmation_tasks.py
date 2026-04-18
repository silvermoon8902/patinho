import asyncio
import logging
from datetime import datetime, timezone

from app.celery_app import celery_app

logger = logging.getLogger(__name__)


async def _auto_resolve_pending_confirmations_async() -> int:
    """
    Find bets in PENDING_CONFIRMATION whose confirmation window has passed.
    If no contestations exist, auto-resolve using the declared winner.
    """
    from sqlalchemy import func, select

    from app.database import async_session_maker
    from app.models.bet import Bet, BetStatus
    from app.models.contestation import Contestation
    from app.services import distribution_service

    async with async_session_maker() as db:
        try:
            now = datetime.now(timezone.utc)

            result = await db.execute(
                select(Bet).where(
                    Bet.status == BetStatus.PENDING_CONFIRMATION,
                    Bet.confirmation_closes_at <= now,
                )
            )
            bets = list(result.scalars().all())

            if not bets:
                logger.debug("No pending confirmations to auto-resolve")
                return 0

            logger.info(
                "Auto-resolving %d bets with expired confirmation windows",
                len(bets),
            )

            resolved_count = 0
            for bet in bets:
                try:
                    count_result = await db.execute(
                        select(func.count())
                        .select_from(Contestation)
                        .where(Contestation.bet_id == bet.id)
                    )
                    contestation_count = count_result.scalar() or 0

                    if contestation_count > 0:
                        logger.info(
                            "Bet %s has %d contestation(s), skipping auto-resolve",
                            bet.id,
                            contestation_count,
                        )
                        continue

                    if not bet.declared_winner_option_id:
                        logger.warning(
                            "Bet %s has no declared winner, skipping", bet.id
                        )
                        continue

                    await distribution_service.distribute_prizes(
                        db, bet.id, bet.declared_winner_option_id
                    )
                    resolved_count += 1
                    logger.info("Auto-resolved bet %s", bet.id)
                except Exception:
                    logger.exception(
                        "Error auto-resolving bet %s", bet.id
                    )
                    continue

            await db.commit()
            logger.info(
                "Auto-resolved %d/%d pending confirmations",
                resolved_count,
                len(bets),
            )
            return resolved_count
        except Exception:
            await db.rollback()
            logger.exception("Error in auto_resolve_pending_confirmations task")
            raise


@celery_app.task(name="app.tasks.confirmation.auto_resolve_pending_confirmations")
def auto_resolve_pending_confirmations() -> int:
    """Celery beat task: auto-resolve bets past their confirmation window."""
    return asyncio.run(_auto_resolve_pending_confirmations_async())
