import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class PaymentResponse(BaseModel):
    id: uuid.UUID
    amount: Decimal
    status: str
    pix_qr_code: str | None
    pix_copy_paste: str | None
    expires_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class MercadoPagoWebhook(BaseModel):
    action: str
    data: dict
