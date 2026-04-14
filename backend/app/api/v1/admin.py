from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.services import admin_service
from app.services.auth_service import get_admin_user

router = APIRouter(tags=["admin"])


class ToggleActiveRequest(BaseModel):
    is_active: bool


class ForceResolveRequest(BaseModel):
    winning_option_id: UUID


class UpdateFeeRequest(BaseModel):
    fee_type: str
    fee_value: float


@router.get("/dashboard")
async def dashboard(
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    return await admin_service.get_dashboard_stats(db)


@router.get("/users")
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    users = await admin_service.list_users(db, skip, limit, search)
    return [
        {
            "id": u.id,
            "email": u.email,
            "username": u.username,
            "phone": u.phone,
            "is_admin": u.is_admin,
            "is_active": u.is_active,
            "total_points": u.total_points,
            "created_at": u.created_at,
        }
        for u in users
    ]


@router.put("/users/{user_id}/toggle-active")
async def toggle_user_active(
    user_id: UUID,
    body: ToggleActiveRequest,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    user = await admin_service.toggle_user_active(db, user_id, body.is_active)
    return {"id": user.id, "is_active": user.is_active}


@router.put("/users/{user_id}/make-admin")
async def make_admin(
    user_id: UUID,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    user = await admin_service.make_admin(db, user_id)
    return {"id": user.id, "is_admin": user.is_admin}


@router.get("/bets")
async def list_bets(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    bets = await admin_service.list_bets(db, skip, limit, status)
    return [
        {
            "id": b.id,
            "title": b.title,
            "category": b.category,
            "status": b.status.value,
            "current_participants": len(b.participations),
            "pot_total": float(sum(p.amount for p in b.participations)),
            "created_at": b.created_at,
            "options": [
                {"id": opt.id, "label": opt.label, "is_winner": opt.is_winner}
                for opt in b.options
            ],
        }
        for b in bets
    ]


@router.post("/bets/{bet_id}/force-resolve")
async def force_resolve_bet(
    bet_id: UUID,
    body: ForceResolveRequest,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    bet = await admin_service.force_resolve_bet(db, bet_id, body.winning_option_id)
    return {"id": bet.id, "status": bet.status.value}


@router.post("/bets/{bet_id}/force-cancel")
async def force_cancel_bet(
    bet_id: UUID,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    bet = await admin_service.force_cancel_bet(db, bet_id)
    return {"id": bet.id, "status": bet.status.value}


@router.get("/config/fee")
async def get_fee_config(
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    return await admin_service.get_fee_config(db)


@router.put("/config/fee")
async def update_fee_config(
    body: UpdateFeeRequest,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    config = await admin_service.update_fee_config(db, body.fee_type, body.fee_value)
    return {"key": config.key, "value": config.value}
