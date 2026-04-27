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
    # Velocity check: cap deposits per user per 24h to deter chargeback/fraud.
    # 10 deposit attempts per 24h and max R$ 5000/day total.
    from sqlalchemy import func

    from app.models.user import User

    now = datetime.now(timezone.utc)
    window_start = now - timedelta(hours=24)
    daily_result = await db.execute(
        select(
            func.count(Payment.id),
            func.coalesce(func.sum(Payment.amount), 0),
        ).where(
            Payment.user_id == user_id,
            Payment.created_at >= window_start,
        )
    )
    row = daily_result.first()
    count_24h, sum_24h = (row or (0, 0))
    if count_24h >= 10:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                "Limite diário de tentativas de depósito atingido. "
                "Tente novamente em algumas horas."
            ),
        )
    if Decimal(str(sum_24h)) + amount > Decimal("5000"):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Limite diário de depósitos (R$ 5.000) seria ultrapassado.",
        )

    user = (
        await db.execute(select(User).where(User.id == user_id))
    ).scalar_one_or_none()

    external_reference = str(uuid.uuid4())

    mp_response = await mp_client.create_pix_payment(
        amount=amount,
        external_reference=external_reference,
        description="Patinho - Deposit",
        payer_email=user.email if user else None,
        payer_first_name=(user.username if user else None),
        payer_last_name="Patinho",
        payer_cpf=getattr(user, "cpf", None) if user else None,
    )

    payment = Payment(
        user_id=user_id,
        mp_payment_id=mp_response.get("id"),
        mp_external_reference=external_reference,
        amount=amount,
        status=PaymentStatus.PENDING,
        pix_qr_code=mp_response.get("qr_code_base64"),
        pix_copy_paste=mp_response.get("copy_paste"),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
    )
    db.add(payment)
    await db.flush()
    return payment


async def _apply_mp_status(
    db: AsyncSession,
    payment: Payment,
    mp_data: dict,
    webhook_data: dict | None = None,
) -> bool:
    """Advance a Payment row based on the freshest MP state. Idempotent.

    Returns True when the payment transitioned to APPROVED in this call —
    lets callers know the wallet was just credited.
    """
    if payment.status == PaymentStatus.APPROVED:
        return False

    mp_status = mp_data.get("status")
    mp_payment_id = str(mp_data.get("id") or payment.mp_payment_id or "")

    metadata = dict(payment.webhook_payload or {})
    is_direct_join = metadata.get("direct_join") is True
    if webhook_data is not None:
        metadata["mp_webhook"] = webhook_data
    metadata["mp_last_poll"] = {"status": mp_status, "id": mp_payment_id}
    payment.webhook_payload = metadata

    if mp_status == "approved":
        payment.status = PaymentStatus.APPROVED
        if mp_payment_id:
            payment.mp_payment_id = mp_payment_id
        if is_direct_join:
            from app.services import direct_join_service
            await direct_join_service.process_direct_join(db, payment.id)
        else:
            await wallet_service.credit_deposit(
                db, payment.user_id, payment.amount, payment.id
            )
        await db.flush()
        return True

    if mp_status in ("rejected", "cancelled"):
        payment.status = PaymentStatus.REJECTED
        await db.flush()
        return False

    return False


async def reconcile_payment(
    db: AsyncSession,
    payment_id: uuid.UUID,
    user_id: uuid.UUID | None = None,
) -> Payment:
    """Pull fresh state from Mercado Pago and reconcile our Payment row.

    Webhook-independent: used by the sync endpoint (when the user paid but the
    webhook never arrived — common on HTTP/IP deploys that MP refuses to
    notify) and by the Celery poller.
    """
    result = await db.execute(select(Payment).where(Payment.id == payment_id))
    payment = result.scalar_one_or_none()
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pagamento não encontrado"
        )
    if user_id is not None and payment.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Pagamento não pertence ao usuário"
        )
    if payment.status == PaymentStatus.APPROVED:
        return payment
    if not payment.mp_payment_id:
        return payment
    try:
        mp_data = await mp_client.get_payment(payment.mp_payment_id)
    except Exception:
        logger.exception("reconcile_payment: MP get_payment failed for %s", payment.id)
        return payment
    await _apply_mp_status(db, payment, mp_data)
    return payment


async def reconcile_user_pending(db: AsyncSession, user_id: uuid.UUID) -> int:
    """Reconcile every still-pending Payment for a user. Returns # approved."""
    result = await db.execute(
        select(Payment).where(
            Payment.user_id == user_id,
            Payment.status == PaymentStatus.PENDING,
        )
    )
    rows = result.scalars().all()
    approved = 0
    for payment in rows:
        if not payment.mp_payment_id:
            continue
        try:
            mp_data = await mp_client.get_payment(payment.mp_payment_id)
        except Exception:
            logger.warning("reconcile_user_pending: MP lookup failed for %s", payment.id)
            continue
        if await _apply_mp_status(db, payment, mp_data):
            approved += 1
    return approved


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

    mp_data = await mp_client.get_payment(mp_payment_id)
    external_reference = mp_data.get("external_reference")
    if not external_reference:
        logger.warning("MP payment %s has no external_reference", mp_payment_id)
        return

    result = await db.execute(
        select(Payment).where(Payment.mp_external_reference == external_reference)
    )
    payment = result.scalar_one_or_none()
    if not payment:
        logger.warning("No payment found for external_reference %s", external_reference)
        return

    await _apply_mp_status(db, payment, mp_data, webhook_data=webhook_data)


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
