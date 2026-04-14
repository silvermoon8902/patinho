from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.services.auth_service import get_current_active_user
from app.services import badge_service, ranking_service

router = APIRouter(tags=["ranking"])


@router.get("/")
async def get_global_leaderboard(db: AsyncSession = Depends(get_db)):
    """Get global leaderboard (top 20, public)."""
    return await ranking_service.get_leaderboard(db, limit=20, weekly=False)


@router.get("/weekly")
async def get_weekly_leaderboard(db: AsyncSession = Depends(get_db)):
    """Get weekly leaderboard (top 20, public)."""
    return await ranking_service.get_leaderboard(db, limit=20, weekly=True)


@router.get("/me")
async def get_my_rank(
    current_user: User = Depends(get_current_active_user),
):
    """Get current user's rank and points."""
    global_rank = await ranking_service.get_user_rank(current_user.id, weekly=False)
    weekly_rank = await ranking_service.get_user_rank(current_user.id, weekly=True)
    return {
        "user_id": str(current_user.id),
        "username": current_user.username,
        "global": global_rank,
        "weekly": weekly_rank,
    }


@router.get("/badges")
async def get_my_badges(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's badges."""
    return await badge_service.get_user_badges(db, current_user.id)


@router.get("/badges/{user_id}")
async def get_user_badges(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get any user's badges (public)."""
    return await badge_service.get_user_badges(db, user_id)
