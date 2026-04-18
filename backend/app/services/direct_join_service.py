import logging
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.mercado_pago import mp_client
from app.models.bet import Bet, BetStatus
from app.models.bet_option import BetOption
from app.models.participation import Participation
from app.models.payment import Payment, PaymentStatus
from app.schemas.bet import BetJoin
from app.services import bet_service, wallet_service

logger = logging.getLogger(__name__)


async def create_direct_join_payment(
    db: AsyncSession,
    user_id: UUID,
    bet_id: UUID,
    option_id: UUID,
    amount: Decimal,
) -> Payment:
    """
    Generate a Pix charge for the exact bet entry amount.
    Stores bet_id and option_id in the payment metadata (webhook_payload field).
    On payment approval, the webhook handler will credit + lock + join in one transaction.
    """
    # Validate bet
    bet = await db.get(Bet, bet_id)
    if not bet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bet not found",
        )

    if bet.status != BetStatus.OPEN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bet is not open for participation",
        )

    if bet.closes_at <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bet entry period has expired",
        )

    # Validate amount matches the bet's fixed entry amount
    if amount != bet.entry_amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Amount must be exactly R${bet.entry_amount}",
        )

    # Validate option
    option = await db.get(BetOption, option_id)
    if not option or option.bet_id != bet_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid bet option for this bet",
        )

    # Check user not already joined
    existing = await db.execute(
        select(Participation).where(
            Participation.bet_id == bet_id,
            Participation.user_id == user_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already joined this bet",
        )

    external_reference = str(uuid.uuid4())

    mp_response = await mp_client.create_pix_payment(
        amount=amount,
        external_reference=external_reference,
        description=f"Patinho - Bet Entry: {bet.title[:50]}",
    )

    payment = Payment(
        user_id=user_id,
        mp_payment_id=mp_response.get("id"),
        mp_external_reference=external_reference,
        amount=amount,
        status=PaymentStatus.PENDING,
        pix_qr_code=mp_response.get("qr_code"),
        pix_copy_paste=mp_response.get("copy_paste"),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
        # Store bet metadata for processing after payment approval
        webhook_payload={
            "direct_join": True,
            "bet_id": str(bet_id),
            "bet_option_id": str(option_id),
        },
    )
    db.add(payment)
    await db.flush()

    logger.info(
        "Direct join payment %s created for user %s, bet %s",
        payment.id,
        user_id,
        bet_id,
    )
    return payment


async def process_direct_join(db: AsyncSession, payment_id: UUID) -> None:
    """
    Called when a direct-join payment is approved via webhook.
    Credits wallet, locks funds, and joins the bet in a single transaction.
    """
    payment = await db.get(Payment, payment_id)
    if not payment:
        logger.warning("Payment %s not found for direct join", payment_id)
        return

    metadata = payment.webhook_payload or {}
    if not metadata.get("direct_join"):
        logger.warning("Payment %s is not a direct join payment", payment_id)
        return

    bet_id = UUID(metadata["bet_id"])
    option_id = UUID(metadata["bet_option_id"])

    # Credit wallet
    await wallet_service.credit_deposit(db, payment.user_id, payment.amount, payment.id)

    # Lock funds and join bet
    await wallet_service.lock_funds(db, payment.user_id, payment.amount, bet_id)

    participation = Participation(
        bet_id=bet_id,
        user_id=payment.user_id,
        bet_option_id=option_id,
        amount=payment.amount,
    )
    db.add(participation)
    await db.flush()

    logger.info(
        "Direct join completed: user %s joined bet %s via payment %s",
        payment.user_id,
        bet_id,
        payment_id,
    )
