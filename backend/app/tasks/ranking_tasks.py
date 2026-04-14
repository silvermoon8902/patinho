import asyncio
import logging
from uuid import UUID

from app.celery_app import celery_app

logger = logging.getLogger(__name__)


async def _reset_weekly_ranking_async() -> None:
    from app.services.ranking_service import reset_weekly_ranking

    await reset_weekly_ranking()


@celery_app.task(name="app.tasks.ranking.reset_weekly_ranking")
def reset_weekly_ranking() -> None:
    """Celery beat task: reset weekly ranking every Monday 00:00."""
    asyncio.run(_reset_weekly_ranking_async())
    logger.info("Weekly ranking reset completed")


async def _award_badges_async(user_id_str: str) -> list[str]:
    from app.database import async_session_maker
    from app.services.badge_service import check_and_award_badges

    async with async_session_maker() as db:
        try:
            awarded = await check_and_award_badges(db, UUID(user_id_str))
            await db.commit()
            return awarded
        except Exception:
            await db.rollback()
            logger.exception("Error awarding badges for user %s", user_id_str)
            raise


@celery_app.task(name="app.tasks.ranking.award_badges_task")
def award_badges_task(user_id: str) -> list[str]:
    """Async task to check and award badges after bet resolution."""
    result = asyncio.run(_award_badges_async(user_id))
    if result:
        logger.info("Awarded badges to user %s: %s", user_id, result)
    return result
