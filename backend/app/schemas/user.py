import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    username: str
    phone: str
    birth_date: date | None
    is_admin: bool
    total_points: int
    created_at: datetime
    self_excluded_at: datetime | None = None
    monthly_deposit_cap: Decimal | None = None
    monthly_participation_cap: Decimal | None = None

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=50)
    phone: str | None = Field(default=None, max_length=20)


class SelfExclusionRequest(BaseModel):
    confirm: bool = Field(
        description="Must be true — confirms the user wants to deactivate their account"
    )


class LimitsUpdate(BaseModel):
    """Set or clear the user's self-imposed monthly caps. None leaves unchanged, 0 clears."""

    monthly_deposit_cap: Decimal | None = Field(default=None, ge=0, le=100000)
    monthly_participation_cap: Decimal | None = Field(default=None, ge=0, le=100000)


class AccountDeletionRequest(BaseModel):
    confirm_email: str = Field(description="Must match the user's email")
    password: str = Field(min_length=1)
