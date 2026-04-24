import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


class BetCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str | None = None
    category: str = Field(min_length=1, max_length=50)
    resolution_type: str = Field(pattern="^(auto_api|voting)$")
    options: list[str] = Field(min_length=2)
    closes_at: datetime
    entry_amount: Decimal = Field(default=Decimal("5"), ge=5, le=1000)
    max_participants: int = Field(default=100, ge=2, le=1000)
    sports_match_id: str | None = None
    league_id: uuid.UUID | None = None

    @field_validator("options")
    @classmethod
    def validate_options(cls, v: list[str]) -> list[str]:
        if len(v) < 2:
            raise ValueError("A bet must have at least 2 options")
        if len(v) != len(set(v)):
            raise ValueError("Options must be unique")
        return v

    @model_validator(mode="after")
    def require_regulamento_on_voting(self) -> "BetCreate":
        """Custom (voting) bets must carry a regulamento so invitees know the
        rules they're accepting. Auto-resolution bets read their rules from
        the sport fixture, so description stays optional there."""
        if self.resolution_type == "voting":
            desc = (self.description or "").strip()
            if len(desc) < 20:
                raise ValueError(
                    "O regulamento do desafio é obrigatório e deve ter ao menos 20 caracteres."
                )
        return self


class BetJoin(BaseModel):
    bet_option_id: uuid.UUID


class BetOptionResponse(BaseModel):
    id: uuid.UUID
    label: str
    is_winner: bool

    model_config = {"from_attributes": True}


class ParticipationResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    username: str
    bet_option_id: uuid.UUID
    amount: Decimal
    prize_amount: Decimal | None

    model_config = {"from_attributes": True}


class BetResponse(BaseModel):
    id: uuid.UUID
    creator_id: uuid.UUID
    title: str
    description: str | None
    invite_token: str
    category: str
    resolution_type: str
    status: str
    entry_amount: Decimal
    max_participants: int
    closes_at: datetime
    resolved_at: datetime | None
    created_at: datetime
    declared_winner_option_id: uuid.UUID | None = None
    declared_at: datetime | None = None
    confirmation_closes_at: datetime | None = None
    league_id: uuid.UUID | None = None
    template: str | None = None
    options: list[BetOptionResponse]
    current_participants: int

    model_config = {"from_attributes": True}


class BetDetailResponse(BetResponse):
    participations: list[ParticipationResponse]


class VoteRequest(BaseModel):
    bet_option_id: uuid.UUID


class VoteCountResponse(BaseModel):
    option_id: uuid.UUID
    label: str
    count: int


class DisputeEvidenceRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    image_url: str | None = Field(default=None, max_length=500)


class DisputeResolveRequest(BaseModel):
    winning_option_id: uuid.UUID


class DirectJoinRequest(BaseModel):
    bet_option_id: uuid.UUID
    amount: Decimal = Field(ge=5, le=1000)


class DeclareWinnerRequest(BaseModel):
    winning_option_id: uuid.UUID


class ContestRequest(BaseModel):
    reason: str | None = None


class ContestationResponse(BaseModel):
    id: uuid.UUID
    bet_id: uuid.UUID
    user_id: uuid.UUID
    reason: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class EmailInviteRequest(BaseModel):
    emails: list[EmailStr] = Field(min_length=1, max_length=10)


class EmailInviteResponse(BaseModel):
    results: dict[str, str]
