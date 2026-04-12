import logging
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.mercado_pago import mp_client
from app.models.payment import Payment, PaymentStatus
from app.services import wallet_service

logger = logging.getLogger(__name__)


async def create_pix_deposit(
    db: AsyncSession, user_id: uuid.UUID, amount: Decimal
) -> Payment:
    """Generate a Pix charge via Mercado Pago and persist the Payment."""
    external_reference = str(uuid.uuid4())

    mp_response = await mp_client.create_pix_payment(
        amount=amount,
        external_reference=external_reference,
        description="Patinho - Deposit",
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
    )
    db.add(payment)
    await db.flush()
    return payment


async def process_webhook(
    db: AsyncSession,
    webhook_data: dict,
    signature: str,
    raw_body: bytes,
) -> None:
    """Process a Mercado Pago payment webhook notification."""
    if not mp_client.verify_webhook_signature(signature, raw_body):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )

    action = webhook_data.get("action")
    if action != "payment.updated" and webhook_data.get("type") != "payment":
        logger.info("Ignoring webhook action: %s", action)
        return

    mp_payment_id = str(
        webhook_data.get("data", {}).get("id", "")
        or webhook_data.get("data_id", "")
    )
    if not mp_payment_id:
        logger.warning("Webhook missing payment ID")
        return

    # Fetch payment details from MP
    mp_data = await mp_client.get_payment(mp_payment_id)
    external_reference = mp_data.get("external_reference")

    if not external_reference:
        logger.warning("MP payment %s has no external_reference", mp_payment_id)
        return

    # Find our payment record
    result = await db.execute(
        select(Payment).where(Payment.mp_external_reference == external_reference)
    )
    payment = result.scalar_one_or_none()

    if not payment:
        logger.warning("No payment found for external_reference %s", external_reference)
        return

    # Idempotency: skip if already processed
    if payment.status == PaymentStatus.APPROVED:
        logger.info("Payment %s already approved, skipping", payment.id)
        return

    mp_status = mp_data.get("status")
    payment.webhook_payload = webhook_data

    if mp_status == "approved":
        payment.status = PaymentStatus.APPROVED
        payment.mp_payment_id = mp_payment_id
        await wallet_service.credit_deposit(
            db, payment.user_id, payment.amount, payment.id
        )
    elif mp_status in ("rejected", "cancelled"):
        payment.status = PaymentStatus.REJECTED
    else:
        logger.info("Unhandled MP status %s for payment %s", mp_status, payment.id)
        return

    await db.flush()


async def expire_pending_payments(db: AsyncSession) -> int:
    """Expire payments that have passed their expires_at timestamp."""
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(Payment).where(
            Payment.status == PaymentStatus.PENDING,
            Payment.expires_at < now,
        )
    )
    payments = result.scalars().all()
    count = 0
    for payment in payments:
        payment.status = PaymentStatus.EXPIRED
        count += 1
    await db.flush()
    return count
