from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.league import (
    LeagueCreate,
    LeagueDetailResponse,
    LeagueInviteRequest,
    LeagueInviteResponse,
    LeagueJoinRequest,
    LeagueRankingEntry,
    LeagueResponse,
)
from app.services import league_service
from app.services.auth_service import get_current_active_user

router = APIRouter(tags=["leagues"])


@router.post("", response_model=LeagueResponse, status_code=201)
async def create_league(
    data: LeagueCreate,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    league = await league_service.create_league(db, user.id, data)
    return league_service.build_league_response(league)


@router.get("", response_model=list[LeagueResponse])
async def list_my_leagues(
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    leagues = await league_service.list_user_leagues(db, user.id)
    return [league_service.build_league_response(lg) for lg in leagues]


@router.post("/join", response_model=LeagueResponse)
async def join_league_by_code(
    data: LeagueJoinRequest,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    league = await league_service.join_by_code(db, user.id, data.invite_code)
    return league_service.build_league_response(league)


@router.get("/{league_id}", response_model=LeagueDetailResponse)
async def get_league_detail(
    league_id: UUID,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    league = await league_service.get_league(db, league_id)
    return league_service.build_league_detail(league, user.id)


@router.post("/{league_id}/invite", response_model=LeagueInviteResponse)
async def invite_to_league(
    league_id: UUID,
    data: LeagueInviteRequest,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    status_str = await league_service.invite_to_league(
        db, league_id, user.id, data.identifier
    )
    return LeagueInviteResponse(status=status_str)


@router.post("/{league_id}/leave", status_code=204)
async def leave_league(
    league_id: UUID,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    await league_service.leave_league(db, league_id, user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/{league_id}/members/{user_id}", status_code=204)
async def remove_member(
    league_id: UUID,
    user_id: UUID,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    await league_service.remove_member(db, league_id, user.id, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/{league_id}", status_code=204)
async def delete_league(
    league_id: UUID,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    await league_service.delete_league(db, league_id, user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{league_id}/ranking", response_model=list[LeagueRankingEntry]
)
async def get_league_ranking(
    league_id: UUID,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    ranking = await league_service.get_league_ranking(db, league_id)
    return [LeagueRankingEntry(**entry) for entry in ranking]
