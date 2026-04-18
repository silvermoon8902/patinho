from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.bet import (
    BetCreate,
    BetDetailResponse,
    BetJoin,
    BetOptionResponse,
    BetResponse,
    ContestationResponse,
    ContestRequest,
    DeclareWinnerRequest,
    DirectJoinRequest,
    DisputeEvidenceRequest,
    DisputeResolveRequest,
    ParticipationResponse,
    VoteCountResponse,
    VoteRequest,
)
from app.schemas.payment import PaymentResponse
from app.services import (
    bet_service,
    declare_service,
    direct_join_service,
    dispute_service,
    voting_service,
)
from app.services.auth_service import get_current_active_user

router = APIRouter(tags=["bets"])


def _build_bet_response(bet) -> dict:
    """Build bet response dict with computed fields."""
    return {
        "id": bet.id,
        "creator_id": bet.creator_id,
        "title": bet.title,
        "description": bet.description,
        "invite_token": bet.invite_token,
        "category": bet.category,
        "resolution_type": bet.resolution_type.value,
        "status": bet.status.value,
        "entry_amount": bet.entry_amount,
        "max_participants": bet.max_participants,
        "closes_at": bet.closes_at,
        "resolved_at": bet.resolved_at,
        "created_at": bet.created_at,
        "declared_winner_option_id": bet.declared_winner_option_id,
        "declared_at": bet.declared_at,
        "confirmation_closes_at": bet.confirmation_closes_at,
        "options": [
            BetOptionResponse.model_validate(opt) for opt in bet.options
        ],
        "current_participants": len(bet.participations),
    }


def _build_detail_response(bet) -> dict:
    """Build detailed bet response with participations."""
    data = _build_bet_response(bet)
    data["participations"] = [
        ParticipationResponse(
            id=p.id,
            user_id=p.user_id,
            username=p.user.username if p.user else "unknown",
            bet_option_id=p.bet_option_id,
            amount=p.amount,
            prize_amount=p.prize_amount,
        )
        for p in bet.participations
    ]
    return data


@router.post("", response_model=BetResponse, status_code=201)
async def create_bet(
    data: BetCreate,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    bet = await bet_service.create_bet(db, user.id, data)
    return _build_bet_response(bet)


@router.get("", response_model=list[BetResponse])
async def list_user_bets(
    status: str | None = Query(default=None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    bets = await bet_service.get_user_bets(db, user.id, status, skip, limit)
    return [_build_bet_response(b) for b in bets]


@router.get("/invite/{invite_token}", response_model=BetResponse)
async def get_bet_by_invite(
    invite_token: str,
    db: AsyncSession = Depends(get_db),
):
    bet = await bet_service.get_bet_by_invite(db, invite_token)
    return _build_bet_response(bet)


@router.get("/{bet_id}", response_model=BetDetailResponse)
async def get_bet_detail(
    bet_id: UUID,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    bet = await bet_service.get_bet(db, bet_id)
    return _build_detail_response(bet)


@router.post("/{bet_id}/join", response_model=ParticipationResponse)
async def join_bet(
    bet_id: UUID,
    data: BetJoin,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    participation = await bet_service.join_bet(db, user.id, bet_id, data)
    return ParticipationResponse(
        id=participation.id,
        user_id=participation.user_id,
        username=user.username,
        bet_option_id=participation.bet_option_id,
        amount=participation.amount,
        prize_amount=participation.prize_amount,
    )


@router.post("/{bet_id}/vote", status_code=201)
async def cast_vote(
    bet_id: UUID,
    data: VoteRequest,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    vote = await voting_service.cast_vote(db, user.id, bet_id, data.bet_option_id)
    return {"id": vote.id, "bet_option_id": vote.bet_option_id}


@router.post("/{bet_id}/dispute", status_code=201)
async def submit_dispute_evidence(
    bet_id: UUID,
    data: DisputeEvidenceRequest,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    evidence = await dispute_service.submit_evidence(
        db, user.id, bet_id, data.text, data.image_url
    )
    return {
        "id": evidence.id,
        "bet_id": evidence.bet_id,
        "text": evidence.text,
        "image_url": evidence.image_url,
        "created_at": evidence.created_at,
    }


@router.post("/{bet_id}/dispute/resolve", status_code=200)
async def resolve_dispute(
    bet_id: UUID,
    data: DisputeResolveRequest,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    await dispute_service.resolve_dispute(db, user.id, bet_id, data.winning_option_id)
    return {"detail": "Dispute resolved"}


@router.post("/{bet_id}/direct-join", response_model=PaymentResponse)
async def create_direct_join(
    bet_id: UUID,
    data: DirectJoinRequest,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    payment = await direct_join_service.create_direct_join_payment(
        db, user.id, bet_id, data.bet_option_id, data.amount
    )
    return payment


@router.post("/{bet_id}/declare-winner", response_model=BetResponse)
async def declare_winner(
    bet_id: UUID,
    data: DeclareWinnerRequest,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    bet = await declare_service.declare_winner(
        db, bet_id, user.id, data.winning_option_id
    )
    # Reload with relationships for response
    bet = await bet_service.get_bet(db, bet_id)
    return _build_bet_response(bet)


@router.post("/{bet_id}/contest", response_model=ContestationResponse, status_code=201)
async def contest_result(
    bet_id: UUID,
    data: ContestRequest,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    contestation = await declare_service.contest_result(
        db, bet_id, user.id, data.reason
    )
    return ContestationResponse.model_validate(contestation)


@router.post("/{bet_id}/accept", status_code=200)
async def accept_result(
    bet_id: UUID,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    await declare_service.accept_result(db, bet_id, user.id)
    return {"detail": "Result accepted"}


@router.get("/{bet_id}/contestations", response_model=list[ContestationResponse])
async def list_contestations(
    bet_id: UUID,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    contestations = await declare_service.get_contestations(db, bet_id)
    return [ContestationResponse.model_validate(c) for c in contestations]
