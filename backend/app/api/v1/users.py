from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.participation import Participation
from app.models.user import User
from app.models.wallet import Wallet
from app.models.wallet_transaction import WalletTransaction
from app.schemas.user import (
    AccountDeletionRequest,
    LimitsUpdate,
    SelfExclusionRequest,
    UserResponse,
    UserUpdate,
)
from app.services.auth_service import get_current_active_user
from app.utils.security import verify_password

router = APIRouter(tags=["users"])


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_active_user)):
    return user


@router.put("/me", response_model=UserResponse)
async def update_me(
    updates: UserUpdate,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    if updates.username is not None:
        result = await db.execute(
            select(User).where(User.username == updates.username, User.id != user.id)
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already taken",
            )
        user.username = updates.username

    if updates.phone is not None:
        user.phone = updates.phone

    await db.flush()
    return user


@router.patch("/me/limits", response_model=UserResponse)
async def update_limits(
    updates: LimitsUpdate,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """User-set monthly caps on themselves. 0 clears the cap. None leaves it unchanged."""
    if updates.monthly_deposit_cap is not None:
        user.monthly_deposit_cap = (
            None if updates.monthly_deposit_cap == 0 else updates.monthly_deposit_cap
        )
    if updates.monthly_participation_cap is not None:
        user.monthly_participation_cap = (
            None
            if updates.monthly_participation_cap == 0
            else updates.monthly_participation_cap
        )
    await db.flush()
    return user


@router.post("/me/self-exclude", status_code=status.HTTP_204_NO_CONTENT)
async def self_exclude(
    data: SelfExclusionRequest,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    User-initiated self-exclusion. Sets is_active=False and records the
    timestamp. User is immediately logged out on next request (get_current_active_user
    will return 403). Reversing requires an admin.
    """
    if not data.confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmação obrigatória",
        )
    user.is_active = False
    user.self_excluded_at = datetime.now(timezone.utc)
    await db.flush()


@router.get("/me/export")
async def export_my_data(
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    LGPD Article 18: portability. Returns all personal data we hold on
    this user, as JSON.
    """
    wallet_result = await db.execute(
        select(Wallet).where(Wallet.user_id == user.id)
    )
    wallet = wallet_result.scalar_one_or_none()

    tx_result = await db.execute(
        select(WalletTransaction).where(WalletTransaction.wallet_id == wallet.id)
        if wallet
        else select(WalletTransaction).where(WalletTransaction.wallet_id == None)  # noqa: E711
    )
    transactions = list(tx_result.scalars().all()) if wallet else []

    part_result = await db.execute(
        select(Participation).where(Participation.user_id == user.id)
    )
    participations = list(part_result.scalars().all())

    def _decimal(v):
        return str(v) if v is not None else None

    return {
        "user": {
            "id": str(user.id),
            "email": user.email,
            "username": user.username,
            "phone": user.phone,
            "cpf": user.cpf,
            "birth_date": user.birth_date.isoformat() if user.birth_date else None,
            "total_points": user.total_points,
            "accepted_terms_at": user.accepted_terms_at.isoformat()
            if user.accepted_terms_at else None,
            "terms_version": user.terms_version,
            "age_acknowledged_at": user.age_acknowledged_at.isoformat()
            if user.age_acknowledged_at else None,
            "self_excluded_at": user.self_excluded_at.isoformat()
            if user.self_excluded_at else None,
            "monthly_deposit_cap": _decimal(user.monthly_deposit_cap),
            "monthly_participation_cap": _decimal(user.monthly_participation_cap),
            "created_at": user.created_at.isoformat(),
        },
        "wallet": {
            "balance_available": _decimal(wallet.balance_available) if wallet else None,
            "balance_locked": _decimal(wallet.balance_locked) if wallet else None,
        } if wallet else None,
        "transactions": [
            {
                "id": str(t.id),
                "type": t.type.value if t.type else None,
                "amount": _decimal(t.amount),
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in transactions
        ],
        "participations": [
            {
                "id": str(p.id),
                "bet_id": str(p.bet_id),
                "bet_option_id": str(p.bet_option_id),
                "amount": _decimal(p.amount),
                "prize_amount": _decimal(p.prize_amount),
            }
            for p in participations
        ],
        "exported_at": datetime.now(timezone.utc).isoformat(),
    }


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_account(
    data: AccountDeletionRequest,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    LGPD Article 18: right to deletion. Anonymizes the user rather than
    hard-deleting — we must keep historical bet/transaction records for
    audit and for other participants. PII is scrubbed; account is
    deactivated and cannot be reactivated.

    Requires re-entering email (confirmation) + current password.
    """
    if data.confirm_email.strip().lower() != (user.email or "").lower():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email de confirmação não confere",
        )
    if not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Senha incorreta",
        )

    # Check for locked funds — user must withdraw/resolve first
    wallet_result = await db.execute(
        select(Wallet).where(Wallet.user_id == user.id)
    )
    wallet = wallet_result.scalar_one_or_none()
    if wallet and wallet.balance_locked and wallet.balance_locked > Decimal("0"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Você tem fundos travados em desafios em aberto. "
                "Aguarde a resolução antes de excluir a conta."
            ),
        )

    # Anonymize PII
    deletion_token = f"deleted-{user.id}"
    user.email = f"{deletion_token}@deleted.local"
    user.username = deletion_token[:50]
    user.phone = ""
    user.cpf = None
    user.hashed_password = ""  # can never log in again
    user.is_active = False
    user.self_excluded_at = datetime.now(timezone.utc)
    await db.flush()
