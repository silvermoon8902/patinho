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


@router.post("/deposit", response_model=PaymentResponse)
async def create_deposit(
    body: DepositRequest,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    payment = await payment_service.create_pix_deposit(db, user.id, body.amount)
    return payment


@router.post("/withdraw", response_model=WalletTransactionResponse)
async def create_withdrawal(
    body: WithdrawalRequest,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await wallet_service.process_withdrawal(db, user.id, body.amount)


@router.get("/transactions", response_model=list[WalletTransactionResponse])
async def list_transactions(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await wallet_service.get_transactions(db, user.id, skip, limit)
