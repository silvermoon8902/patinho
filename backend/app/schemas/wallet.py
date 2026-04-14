import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class WalletResponse(BaseModel):
    id: uuid.UUID
    balance: Decimal
    locked_balance: Decimal

    model_config = {"from_attributes": True}


class DepositRequest(BaseModel):
    amount: Decimal = Field(gt=0, le=10000)


class WithdrawalRequest(BaseModel):
    amount: Decimal = Field(ge=20, description="Valor minimo para saque: R$ 20,00")
    pix_key: str


class WalletTransactionResponse(BaseModel):
    id: uuid.UUID
    type: str
    amount: Decimal
    balance_before: Decimal
    balance_after: Decimal
    description: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
