import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.payment import PaymentResponse
from app.schemas.wallet import (
    DepositRequest,
    WalletResponse,
    WalletTransactionResponse,
    WithdrawalRequest,
)
from app.services.auth_service import get_current_active_user
from app.services import payment_service, wallet_service

router = APIRouter(tags=["wallet"])


@router.get("", response_model=WalletResponse)
async def get_wallet(
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await wallet_service.get_wallet(db, user.id)


@router.get("/payment-mode")
async def get_payment_mode(user: User = Depends(get_current_active_user)):
    """Tell the client whether the deposit flow is running on TEST Pix credentials."""
    from app.config import settings

    tok = settings.MERCADO_PAGO_ACCESS_TOKEN or ""
    if getattr(settings, "MERCADO_PAGO_SIMULATED", False):
        mode = "simulated"
    elif tok.startswith("TEST-"):
        mode = "test"
    elif tok:
        mode = "live"
    else:
        mode = "unconfigured"
    return {"mode": mode}


@router.post("/deposit", response_model=PaymentResponse)
async def create_deposit(
    body: DepositRequest,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    payment = await payment_service.create_pix_deposit(db, user.id, body.amount)
    return payment


@router.post("/deposit/{payment_id}/reconcile", response_model=WalletResponse)
async def reconcile_deposit(
    payment_id: uuid.UUID,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Check a specific Pix deposit against Mercado Pago and credit if paid.

    Client-side safety net: when our webhook endpoint can't be reached from
    MP (e.g. plain-HTTP VPS), the frontend polls this to pull status directly.
    """
    await payment_service.reconcile_payment(db, payment_id, user_id=user.id)
    return await wallet_service.get_wallet(db, user.id)


@router.post("/reconcile-pending", response_model=WalletResponse)
async def reconcile_all_pending(
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Reconcile every pending deposit for the authed user. Returns fresh wallet."""
    await payment_service.reconcile_user_pending(db, user.id)
    return await wallet_service.get_wallet(db, user.id)


@router.post("/withdraw", response_model=WalletTransactionResponse)
async def create_withdrawal(
    body: WithdrawalRequest,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await wallet_service.process_withdrawal(
        db, user.id, body.amount, body.pix_key
    )


@router.get("/transactions", response_model=list[WalletTransactionResponse])
async def list_transactions(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await wallet_service.get_transactions(db, user.id, skip, limit)
