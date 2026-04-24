import asyncio
import logging

from app.celery_app import celery_app

logger = logging.getLogger(__name__)


async def _process_webhook_async(payment_data: dict) -> None:
    """Run the async webhook processing within a fresh async DB session."""
    from app.database import async_session_maker
    from app.services import payment_service

    signature = payment_data.pop("_signature", "")
    raw_body = payment_data.pop("_raw_body", "").encode("utf-8")

    async with async_session_maker() as db:
        try:
            await payment_service.process_webhook(db, payment_data, signature, raw_body)
            await db.commit()
        except Exception:
            await db.rollback()
            logger.exception("Error processing payment webhook in Celery task")
            raise


async def _expire_payments_async() -> int:
    from app.database import async_session_maker
    from app.services import payment_service

    async with async_session_maker() as db:
        try:
            count = await payment_service.expire_pending_payments(db)
            await db.commit()
            return count
        except Exception:
            await db.rollback()
            logger.exception("Error expiring pending payments in Celery task")
            raise


async def _reconcile_pending_async() -> int:
    """Pull fresh status from MP for every still-pending payment, system-wide.

    Safety net for deploys where MP webhooks cannot reach us (HTTP/IP hosts).
    Hits the MP API for each pending Payment; idempotent.
    """
    from sqlalchemy import select

    from app.database import async_session_maker
    from app.integrations.mercado_pago import mp_client
    from app.models.payment import Payment, PaymentStatus
    from app.services import payment_service

    approved = 0
    async with async_session_maker() as db:
        try:
            rows = (
                await db.execute(
                    select(Payment).where(Payment.status == PaymentStatus.PENDING)
                )
            ).scalars().all()
            for payment in rows:
                if not payment.mp_payment_id:
                    continue
                try:
                    mp_data = await mp_client.get_payment(payment.mp_payment_id)
                except Exception:
                    logger.warning(
                        "reconcile_pending: MP lookup failed for %s", payment.id
                    )
                    continue
                if await payment_service._apply_mp_status(db, payment, mp_data):
                    approved += 1
            await db.commit()
        except Exception:
            await db.rollback()
            logger.exception("Error reconciling pending payments in Celery task")
            raise
    return approved


@celery_app.task(name="app.tasks.payments.process_payment_webhook")
def process_payment_webhook(payment_data: dict) -> None:
    """Process a Mercado Pago webhook notification asynchronously via Celery."""
    asyncio.run(_process_webhook_async(payment_data))


@celery_app.task(name="app.tasks.payments.expire_pending_payments")
def expire_pending_payments() -> int:
    """Expire pending payments past their expiration time. Called by Celery beat."""
    count = asyncio.run(_expire_payments_async())
    logger.info("Expired %d pending payments", count)
    return count


@celery_app.task(name="app.tasks.payments.reconcile_pending_payments")
def reconcile_pending_payments() -> int:
    """Reconcile every still-pending Payment against the MP API. Beat-driven."""
    count = asyncio.run(_reconcile_pending_async())
    logger.info("Reconciled %d pending payments (approved)", count)
    return count
