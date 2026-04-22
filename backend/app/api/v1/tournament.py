"""Tournament bet endpoints (Bolão da Copa et al.)."""
from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.services import tournament_service
from app.services.auth_service import get_current_active_user

router = APIRouter(tags=["tournament"])


class TournamentBetCreate(BaseModel):
    template_code: str = Field(min_length=3, max_length=60)
    entry_amount: Decimal = Field(ge=5, le=1000)
    max_participants: int = Field(ge=2, le=500)


class PalpiteItem(BaseModel):
    fixture_id: str
    home_score: int = Field(ge=0, le=20)
    away_score: int = Field(ge=0, le=20)
    phase: str | None = "group"
    locks_at: str | None = None


class PalpitesBulkRequest(BaseModel):
    palpites: list[PalpiteItem] = Field(min_length=1, max_length=100)


class ChampionPalpiteRequest(BaseModel):
    team: str = Field(min_length=1, max_length=100)


@router.post("/bets/tournament", status_code=201)
async def create_tournament(
    data: TournamentBetCreate,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    bet = await tournament_service.create_tournament_bet(
        db, user.id, data.template_code, data.entry_amount, data.max_participants
    )
    return {
        "id": str(bet.id),
        "title": bet.title,
        "template": bet.template,
        "invite_token": bet.invite_token,
    }


@router.get("/bets/{bet_id}/palpites")
async def get_palpites(
    bet_id: UUID,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    fixtures = await tournament_service.list_fixtures_for_bet(db, bet_id)
    existing = await tournament_service.get_user_palpites(db, bet_id, user.id)
    enriched = []
    for f in fixtures:
        p = existing.get(f["fixture_id"])
        enriched.append({
            **f,
            "my_palpite": {
                "home_score": p.predicted_home_score if p else None,
                "away_score": p.predicted_away_score if p else None,
                "points_earned": p.points_earned if p else 0,
            } if p else None,
        })
    return {"fixtures": enriched}


@router.post("/bets/{bet_id}/palpites/bulk")
async def submit_palpites_bulk(
    bet_id: UUID,
    data: PalpitesBulkRequest,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await tournament_service.submit_palpites_bulk(
        db, bet_id, user.id, [p.model_dump() for p in data.palpites]
    )
    return result


@router.post("/bets/{bet_id}/champion-palpite")
async def submit_champion(
    bet_id: UUID,
    data: ChampionPalpiteRequest,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    row = await tournament_service.submit_champion_palpite(
        db, bet_id, user.id, data.team
    )
    return {"predicted_champion": row.predicted_champion}


@router.get("/bets/{bet_id}/ranking")
async def get_ranking(
    bet_id: UUID,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return {"ranking": await tournament_service.get_ranking(db, bet_id)}
