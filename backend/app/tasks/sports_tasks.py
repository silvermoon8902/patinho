import asyncio
import logging

from app.celery_app import celery_app

logger = logging.getLogger(__name__)


async def _check_sports_results_async() -> int:
    """
    Query active locked sports bets. Batch fixture IDs.
    Call API-Football. Resolve bets with finished matches.
    """
    from sqlalchemy import select

    from app.database import async_session_maker
    from app.integrations.api_football import api_football_client
    from app.models.bet import Bet, BetStatus, ResolutionType
    from app.services.resolution_service import resolve_sports_bet

    async with async_session_maker() as db:
        try:
            # Find locked sports bets
            result = await db.execute(
                select(Bet).where(
                    Bet.status == BetStatus.LOCKED,
                    Bet.resolution_type == ResolutionType.AUTO_API,
                    Bet.sports_match_id.isnot(None),
                )
            )
            bets = list(result.scalars().all())

            if not bets:
                logger.debug("No locked sports bets to check")
                return 0

            logger.info("Checking %d locked sports bets", len(bets))

            # Batch fetch fixture results
            fixture_ids = [b.sports_match_id for b in bets if b.sports_match_id]
            if fixture_ids:
                # Pre-warm cache with batch request
                await api_football_client.get_fixtures(fixture_ids)

            resolved_count = 0
            for bet in bets:
                try:
                    was_resolved = await resolve_sports_bet(db, bet.id)
                    if was_resolved:
                        resolved_count += 1
                except Exception:
                    logger.exception("Error resolving sports bet %s", bet.id)
                    await db.rollback()
                    continue

            await db.commit()
            logger.info("Resolved %d/%d sports bets", resolved_count, len(bets))
            return resolved_count
        except Exception:
            await db.rollback()
            logger.exception("Error in check_sports_results task")
            raise


@celery_app.task(name="app.tasks.sports.check_sports_results")
def check_sports_results() -> int:
    """Celery beat task: check and resolve sports bets."""
    return asyncio.run(_check_sports_results_async())
