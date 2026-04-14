import logging
from uuid import UUID

import redis.asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import User

logger = logging.getLogger(__name__)

RANKING_KEY = "ranking:global"
RANKING_WEEKLY_KEY = "ranking:weekly"

POINTS_WIN = 100
POINTS_PARTICIPATE = 10
POINTS_CREATE = 5

_redis: aioredis.Redis | None = None


async def _get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis


async def add_points(user_id: UUID, points: int, db: AsyncSession) -> None:
    """Add points to Redis sorted sets and update user.total_points in DB."""
    r = await _get_redis()
    uid = str(user_id)

    await r.zincrby(RANKING_KEY, points, uid)
    await r.zincrby(RANKING_WEEKLY_KEY, points, uid)

    user = await db.get(User, user_id)
    if user:
        user.total_points = (user.total_points or 0) + points
        await db.flush()

    logger.info("Added %d points to user %s", points, user_id)


async def get_leaderboard(
    db: AsyncSession, limit: int = 20, weekly: bool = False
) -> list[dict]:
    """Get top N from Redis sorted set with usernames from DB."""
    r = await _get_redis()
    key = RANKING_WEEKLY_KEY if weekly else RANKING_KEY

    entries = await r.zrevrange(key, 0, limit - 1, withscores=True)

    if not entries:
        return []

    user_ids = [UUID(uid) for uid, _ in entries]
    result = await db.execute(select(User).where(User.id.in_(user_ids)))
    users_map = {str(u.id): u.username for u in result.scalars().all()}

    leaderboard = []
    for rank, (uid, score) in enumerate(entries, start=1):
        leaderboard.append(
            {
                "user_id": uid,
                "username": users_map.get(uid, "???"),
                "points": int(score),
                "rank": rank,
            }
        )

    return leaderboard


async def get_user_rank(
    user_id: UUID, weekly: bool = False
) -> dict:
    """Get specific user's rank and points from Redis."""
    r = await _get_redis()
    key = RANKING_WEEKLY_KEY if weekly else RANKING_KEY
    uid = str(user_id)

    score = await r.zscore(key, uid)
    if score is None:
        return {"user_id": uid, "rank": None, "points": 0}

    rank = await r.zrevrank(key, uid)

    return {
        "user_id": uid,
        "rank": (rank + 1) if rank is not None else None,
        "points": int(score),
    }


async def sync_leaderboard_from_db(db: AsyncSession) -> int:
    """Rebuild Redis global sorted set from DB user.total_points."""
    r = await _get_redis()
    await r.delete(RANKING_KEY)

    result = await db.execute(
        select(User).where(User.total_points > 0)
    )
    users = list(result.scalars().all())

    if not users:
        return 0

    mapping = {str(u.id): u.total_points for u in users}
    await r.zadd(RANKING_KEY, mapping)

    logger.info("Synced leaderboard from DB: %d users", len(users))
    return len(users)


async def reset_weekly_ranking() -> None:
    """Delete weekly Redis key. Called by Celery beat Monday 00:00."""
    r = await _get_redis()
    await r.delete(RANKING_WEEKLY_KEY)
    logger.info("Weekly ranking reset")
