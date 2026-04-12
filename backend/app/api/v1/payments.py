import logging

from fastapi import APIRouter, BackgroundTasks, Header, Request, Response

from app.database import async_session_maker
from app.services import payment_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["payments"])


async def _process_webhook_background(webhook_data: dict, signature: str, raw_body: bytes):
    """Process webhook in background to return 200 quickly to Mercado Pago."""
    async with async_session_maker() as db:
        try:
            await payment_service.process_webhook(db, webhook_data, signature, raw_body)
            await db.commit()
        except Exception:
            await db.rollback()
            logger.exception("Error processing MP webhook in background")


@router.post("/webhook/mercadopago")
async def mercadopago_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_signature: str = Header("", alias="x-signature"),
):
    """Receive Mercado Pago webhook. Returns 200 immediately and processes in background."""
    raw_body = await request.body()
    webhook_data = await request.json()

    background_tasks.add_task(
        _process_webhook_background,
        webhook_data,
        x_signature,
        raw_body,
    )

    return Response(status_code=200)
