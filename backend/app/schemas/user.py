import uuid
from datetime import date, datetime

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

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=50)
    phone: str | None = Field(default=None, max_length=20)
