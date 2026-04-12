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
