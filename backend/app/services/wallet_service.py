from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.wallet import Wallet
from app.models.wallet_transaction import TransactionType, WalletTransaction


async def get_wallet(db: AsyncSession, user_id: UUID) -> Wallet:
    result = await db.execute(select(Wallet).where(Wallet.user_id == user_id))
    wallet = result.scalar_one_or_none()
    if not wallet:
        wallet = Wallet(user_id=user_id)
        db.add(wallet)
        await db.flush()
    return wallet


async def _lock_wallet(db: AsyncSession, user_id: UUID) -> Wallet:
    """Acquire a row-level lock on the wallet. Must be called within a transaction."""
    result = await db.execute(
        select(Wallet).where(Wallet.user_id == user_id).with_for_update()
    )
    wallet = result.scalar_one_or_none()
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found",
        )
    return wallet


async def lock_funds(
    db: AsyncSession, user_id: UUID, amount: Decimal, bet_id: UUID
) -> WalletTransaction:
    """Lock funds for a bet. Deducts from balance, adds to locked_balance."""
    wallet = await _lock_wallet(db, user_id)
    balance_before = wallet.balance

    if wallet.balance < amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Saldo insuficiente",
        )

    wallet.balance -= amount
    wallet.locked_balance += amount

    tx = WalletTransaction(
        wallet_id=wallet.id,
        type=TransactionType.BET_LOCK,
        amount=amount,
        balance_before=balance_before,
        balance_after=wallet.balance,
        reference_id=bet_id,
        description=f"Funds locked for bet {bet_id}",
    )
    db.add(tx)
    await db.flush()
    return tx


async def unlock_funds(
    db: AsyncSession, user_id: UUID, amount: Decimal, bet_id: UUID
) -> WalletTransaction:
    """Unlock funds after losing a bet. Reduces locked_balance, no credit."""
    wallet = await _lock_wallet(db, user_id)
    balance_before = wallet.balance

    wallet.locked_balance -= amount

    tx = WalletTransaction(
        wallet_id=wallet.id,
        type=TransactionType.BET_UNLOCK,
        amount=amount,
        balance_before=balance_before,
        balance_after=wallet.balance,
        reference_id=bet_id,
        description=f"Funds unlocked (loss) for bet {bet_id}",
    )
    db.add(tx)
    await db.flush()
    return tx


async def unlock_and_credit_prize(
    db: AsyncSession,
    user_id: UUID,
    lock_amount: Decimal,
    prize_amount: Decimal,
    bet_id: UUID,
) -> WalletTransaction:
    """Unlock funds and credit prize for a winning bet."""
    wallet = await _lock_wallet(db, user_id)
    balance_before = wallet.balance

    wallet.locked_balance -= lock_amount
    wallet.balance += prize_amount

    tx = WalletTransaction(
        wallet_id=wallet.id,
        type=TransactionType.PRIZE_CREDIT,
        amount=prize_amount,
        balance_before=balance_before,
        balance_after=wallet.balance,
        reference_id=bet_id,
        description=f"Prize credited for bet {bet_id}",
    )
    db.add(tx)
    await db.flush()
    return tx


async def credit_deposit(
    db: AsyncSession, user_id: UUID, amount: Decimal, payment_id: UUID
) -> WalletTransaction:
    """Credit a deposit to the user's wallet."""
    wallet = await _lock_wallet(db, user_id)
    balance_before = wallet.balance

    wallet.balance += amount

    tx = WalletTransaction(
        wallet_id=wallet.id,
        type=TransactionType.DEPOSIT,
        amount=amount,
        balance_before=balance_before,
        balance_after=wallet.balance,
        reference_id=payment_id,
        description="Pix deposit",
    )
    db.add(tx)
    await db.flush()
    return tx


async def process_withdrawal(
    db: AsyncSession, user_id: UUID, amount: Decimal
) -> WalletTransaction:
    """Process a withdrawal from the user's wallet."""
    wallet = await _lock_wallet(db, user_id)
    balance_before = wallet.balance

    if wallet.balance < amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Saldo insuficiente",
        )

    wallet.balance -= amount

    tx = WalletTransaction(
        wallet_id=wallet.id,
        type=TransactionType.WITHDRAWAL,
        amount=amount,
        balance_before=balance_before,
        balance_after=wallet.balance,
        description="Withdrawal request",
    )
    db.add(tx)
    await db.flush()
    return tx


async def get_transactions(
    db: AsyncSession, user_id: UUID, skip: int = 0, limit: int = 20
) -> list[WalletTransaction]:
    wallet = await get_wallet(db, user_id)
    result = await db.execute(
        select(WalletTransaction)
        .where(WalletTransaction.wallet_id == wallet.id)
        .order_by(WalletTransaction.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())
