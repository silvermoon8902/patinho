from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class LeagueCreate(BaseModel):
    name: str = Field(min_length=3, max_length=80)
    description: str | None = Field(default=None, max_length=500)


class LeagueInviteRequest(BaseModel):
    # Accept either email or username — we resolve to a user
    identifier: str = Field(min_length=3, max_length=100)


class LeagueJoinRequest(BaseModel):
    invite_code: str = Field(min_length=3, max_length=12)


class LeagueMemberResponse(BaseModel):
    user_id: UUID
    username: str
    joined_at: datetime
    is_owner: bool

    model_config = {"from_attributes": True}


class LeagueResponse(BaseModel):
    id: UUID
    owner_id: UUID
    name: str
    description: str | None
    invite_code: str
    created_at: datetime
    member_count: int

    model_config = {"from_attributes": True}


class LeagueDetailResponse(LeagueResponse):
    members: list[LeagueMemberResponse]
    is_member: bool
    is_owner: bool


class LeagueRankingEntry(BaseModel):
    user_id: UUID
    username: str
    total_points: int
    wins: int
    participations: int


class LeagueInviteResponse(BaseModel):
    status: str  # "added" | "already_member" | "user_not_found"
