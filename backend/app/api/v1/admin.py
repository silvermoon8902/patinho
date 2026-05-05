from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.admin_action import AdminAction
from app.models.chat_message import ChatMessage
from app.models.user import User
from app.services import admin_service, audit_service
from app.services.auth_service import get_admin_user

router = APIRouter(tags=["admin"])


class ToggleActiveRequest(BaseModel):
    is_active: bool


class ForceResolveRequest(BaseModel):
    winning_option_id: UUID


class UpdateFeeRequest(BaseModel):
    fee_type: str
    fee_value: float


class TestEmailRequest(BaseModel):
    to: str | None = None


@router.get("/dashboard")
async def dashboard(
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    return await admin_service.get_dashboard_stats(db)


@router.post("/tasks/run-lock-expired")
async def run_lock_expired_now(
    admin: User = Depends(get_admin_user),
):
    """Manually trigger the lock_expired_bets task from the API.

    Used to diagnose whether the celery_beat scheduler is what's stuck.
    Returns the count of bets locked.
    """
    from app.tasks.betting_tasks import _lock_expired_bets_async
    count = await _lock_expired_bets_async()
    return {"locked": count}


@router.get("/funnel")
async def funnel(
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Aggregate user-journey counts so we can see where users drop off.

    Each step is a SQL count of distinct users that reached that stage.
    Cheap to compute and lives off existing tables — no new schema.
    """
    from sqlalchemy import func, select

    from app.models.bet import Bet
    from app.models.participation import Participation
    from app.models.payment import Payment, PaymentStatus

    total_users = (
        await db.execute(select(func.count(User.id)))
    ).scalar() or 0
    users_initiated_deposit = (
        await db.execute(select(func.count(func.distinct(Payment.user_id))))
    ).scalar() or 0
    users_approved_deposit = (
        await db.execute(
            select(func.count(func.distinct(Payment.user_id))).where(
                Payment.status == PaymentStatus.APPROVED
            )
        )
    ).scalar() or 0
    users_joined_bet = (
        await db.execute(
            select(func.count(func.distinct(Participation.user_id)))
        )
    ).scalar() or 0
    users_created_bet = (
        await db.execute(
            select(func.count(func.distinct(Bet.creator_id)))
        )
    ).scalar() or 0

    def pct(n: int) -> float:
        return round(100.0 * n / total_users, 1) if total_users else 0.0

    return {
        "total_users": total_users,
        "steps": [
            {"step": "registered", "users": total_users, "pct": 100.0},
            {
                "step": "initiated_deposit",
                "users": users_initiated_deposit,
                "pct": pct(users_initiated_deposit),
            },
            {
                "step": "approved_deposit",
                "users": users_approved_deposit,
                "pct": pct(users_approved_deposit),
            },
            {
                "step": "joined_any_bet",
                "users": users_joined_bet,
                "pct": pct(users_joined_bet),
            },
            {
                "step": "created_any_bet",
                "users": users_created_bet,
                "pct": pct(users_created_bet),
            },
        ],
    }


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


@router.post("/test-email")
async def send_test_email(
    body: TestEmailRequest,
    admin: User = Depends(get_admin_user),
):
    """
    Send a canary email so the admin can verify SMTP config without creating
    a fake account or triggering the password-reset flow. Sends to the
    admin's own email unless `to` is provided.
    """
    from app.config import settings
    from app.services import email_service

    target = body.to or admin.email
    configured = bool(settings.SMTP_HOST)
    if not configured:
        return {
            "configured": False,
            "sent": False,
            "detail": (
                "SMTP_HOST não está configurado. Defina as variáveis "
                "SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, "
                "SMTP_FROM_EMAIL no ambiente do backend e reinicie."
            ),
        }
    html = (
        "<p>Este é um e-mail de teste do Patinho.</p>"
        f"<p>Enviado por: {admin.email}</p>"
        f"<p>Servidor: {settings.SMTP_HOST}:{settings.SMTP_PORT}</p>"
    )
    text = (
        "Este é um e-mail de teste do Patinho.\n"
        f"Enviado por: {admin.email}\n"
        f"Servidor: {settings.SMTP_HOST}:{settings.SMTP_PORT}"
    )
    sent = await email_service.send_email(
        to=target,
        subject="Patinho — teste de SMTP",
        html=html,
        text=text,
    )
    return {
        "configured": True,
        "sent": sent,
        "to": target,
        "host": settings.SMTP_HOST,
        "detail": (
            "E-mail enviado com sucesso." if sent
            else "Envio falhou. Verifique os logs do backend para o erro SMTP."
        ),
    }


@router.get("/payments/mode")
async def payment_mode(admin: User = Depends(get_admin_user)):
    """Report whether Mercado Pago is on TEST or LIVE credentials."""
    from app.config import settings

    tok = settings.MERCADO_PAGO_ACCESS_TOKEN or ""
    mode = "test" if tok.startswith("TEST-") else ("live" if tok else "unconfigured")
    return {"mode": mode, "configured": bool(tok)}


# ================================================================
# Admin audit log + reactivation + chat moderation
# ================================================================


@router.get("/audit")
async def list_audit_log(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    action: str | None = Query(None),
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """List admin audit actions, newest first."""
    stmt = select(AdminAction).order_by(AdminAction.created_at.desc())
    if action:
        stmt = stmt.where(AdminAction.action == action)
    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    rows = list(result.scalars().all())
    # Enrich with admin usernames
    admin_ids = {r.admin_id for r in rows}
    admin_ids |= {r.target_user_id for r in rows if r.target_user_id}
    users_map: dict = {}
    if admin_ids:
        u_result = await db.execute(
            select(User).where(User.id.in_(list(admin_ids)))
        )
        for u in u_result.scalars().all():
            users_map[u.id] = u.username
    return [
        {
            "id": str(r.id),
            "action": r.action,
            "admin_username": users_map.get(r.admin_id, "?"),
            "target_username": users_map.get(r.target_user_id)
            if r.target_user_id else None,
            "target_bet_id": str(r.target_bet_id) if r.target_bet_id else None,
            "metadata": r.action_metadata,
            "ip_address": r.ip_address,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


class ReactivateUserRequest(BaseModel):
    reason: str | None = None


@router.post("/users/{user_id}/reactivate", status_code=200)
async def reactivate_user(
    user_id: UUID,
    body: ReactivateUserRequest,
    request: Request,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Undo a self-exclusion or admin deactivation. Sets is_active=true and clears self_excluded_at."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado",
        )
    if user.email.endswith("@deleted.local"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Conta anonimizada não pode ser reativada",
        )
    user.is_active = True
    user.self_excluded_at = None
    await db.flush()
    await audit_service.record(
        db,
        admin_id=admin.id,
        action="user.reactivate",
        target_user_id=user.id,
        metadata={"reason": body.reason},
        request=request,
    )
    return {"id": str(user.id), "is_active": user.is_active}


class ModerateChatMessageRequest(BaseModel):
    reason: str | None = None


@router.post("/chat/messages/{message_id}/delete", status_code=200)
async def delete_chat_message(
    message_id: UUID,
    body: ModerateChatMessageRequest,
    request: Request,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a chat message. Stays in DB for audit but hidden from clients."""
    result = await db.execute(
        select(ChatMessage).where(ChatMessage.id == message_id)
    )
    msg = result.scalar_one_or_none()
    if not msg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mensagem não encontrada",
        )
    if msg.deleted_at:
        return {"detail": "already deleted"}
    msg.deleted_at = datetime.now(timezone.utc)
    msg.deleted_by = admin.id
    await db.flush()
    await audit_service.record(
        db,
        admin_id=admin.id,
        action="chat.delete_message",
        target_user_id=msg.user_id,
        target_bet_id=msg.bet_id,
        metadata={"message_id": str(msg.id), "reason": body.reason},
        request=request,
    )
    return {"detail": "deleted", "message_id": str(msg.id)}
