import secrets
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.bet import Bet, BetStatus, ResolutionType
from app.models.bet_option import BetOption
from app.models.participation import Participation
from app.schemas.bet import BetCreate, BetJoin
from app.services import wallet_service


async def create_bet(db: AsyncSession, user_id: UUID, data: BetCreate) -> Bet:
    """Create a new bet with options. Validates active bet limit."""
    active_count = await get_active_bet_count(db, user_id)
    if active_count >= 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum of 10 active bets reached",
        )

    if data.closes_at.tzinfo is None:
        closes_at = data.closes_at.replace(tzinfo=timezone.utc)
    else:
        closes_at = data.closes_at

    if closes_at <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="closes_at must be in the future",
        )

    invite_token = secrets.token_urlsafe(16)

    bet = Bet(
        creator_id=user_id,
        title=data.title,
        description=data.description,
        invite_token=invite_token,
        category=data.category,
        resolution_type=ResolutionType(data.resolution_type),
        status=BetStatus.OPEN,
        min_entry=data.min_entry,
        max_entry=data.max_entry,
        max_participants=data.max_participants,
        sports_match_id=data.sports_match_id,
        closes_at=closes_at,
    )
    db.add(bet)
    await db.flush()

    for label in data.options:
        option = BetOption(bet_id=bet.id, label=label)
        db.add(option)

    await db.flush()

    return await get_bet(db, bet.id)


async def get_bet(db: AsyncSession, bet_id: UUID) -> Bet:
    """Get a bet with options and participations eagerly loaded."""
    result = await db.execute(
        select(Bet)
        .where(Bet.id == bet_id)
        .options(
            selectinload(Bet.options).selectinload(BetOption.participations),
            selectinload(Bet.participations).selectinload(Participation.user),
        )
    )
    bet = result.scalar_one_or_none()
    if not bet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bet not found",
        )
    return bet


async def get_bet_by_invite(db: AsyncSession, invite_token: str) -> Bet:
    """Get a bet by its invite token (public access)."""
    result = await db.execute(
        select(Bet)
        .where(Bet.invite_token == invite_token)
        .options(
            selectinload(Bet.options),
            selectinload(Bet.participations).selectinload(Participation.user),
        )
    )
    bet = result.scalar_one_or_none()
    if not bet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bet not found",
        )
    return bet


async def join_bet(
    db: AsyncSession, user_id: UUID, bet_id: UUID, data: BetJoin
) -> Participation:
    """Join a bet by placing a participation. Locks funds from wallet."""
    bet = await get_bet(db, bet_id)

    if bet.status != BetStatus.OPEN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bet is not open for participation",
        )

    if bet.closes_at <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bet entry period has expired",
        )

    # Check user not already joined
    existing = await db.execute(
        select(Participation).where(
            Participation.bet_id == bet_id,
            Participation.user_id == user_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already joined this bet",
        )

    # Check max participants
    participant_count = await db.execute(
        select(func.count()).select_from(Participation).where(
            Participation.bet_id == bet_id
        )
    )
    count = participant_count.scalar() or 0
    if count >= bet.max_participants:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum number of participants reached",
        )

    # Validate amount within bet limits
    if data.amount < bet.min_entry or data.amount > bet.max_entry:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Amount must be between R${bet.min_entry} and R${bet.max_entry}",
        )

    # Validate option belongs to this bet
    option_ids = {opt.id for opt in bet.options}
    if data.bet_option_id not in option_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid bet option for this bet",
        )

    # Lock funds in wallet
    await wallet_service.lock_funds(db, user_id, data.amount, bet_id)

    participation = Participation(
        bet_id=bet_id,
        user_id=user_id,
        bet_option_id=data.bet_option_id,
        amount=data.amount,
    )
    db.add(participation)
    await db.flush()

    return participation


async def get_user_bets(
    db: AsyncSession,
    user_id: UUID,
    status_filter: str | None = None,
    skip: int = 0,
    limit: int = 20,
) -> list[Bet]:
    """List bets where user is creator or participant."""
    # Get bet IDs where user participates
    participation_subq = (
        select(Participation.bet_id)
        .where(Participation.user_id == user_id)
        .subquery()
    )

    query = (
        select(Bet)
        .where(
            (Bet.creator_id == user_id) | (Bet.id.in_(select(participation_subq)))
        )
        .options(
            selectinload(Bet.options),
            selectinload(Bet.participations),
        )
        .order_by(Bet.created_at.desc())
        .offset(skip)
        .limit(limit)
    )

    if status_filter:
        try:
            bet_status = BetStatus(status_filter)
            query = query.where(Bet.status == bet_status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status filter: {status_filter}",
            )

    result = await db.execute(query)
    return list(result.scalars().all())


async def get_active_bet_count(db: AsyncSession, user_id: UUID) -> int:
    """Count bets where user participates and status is active."""
    active_statuses = [
        BetStatus.OPEN,
        BetStatus.LOCKED,
        BetStatus.VOTING,
        BetStatus.DISPUTED,
    ]

    # Count as creator
    creator_count_result = await db.execute(
        select(func.count())
        .select_from(Bet)
        .where(
            Bet.creator_id == user_id,
            Bet.status.in_(active_statuses),
        )
    )
    creator_count = creator_count_result.scalar() or 0

    # Count as participant (not creator)
    participant_subq = (
        select(Participation.bet_id)
        .where(Participation.user_id == user_id)
        .subquery()
    )
    participant_count_result = await db.execute(
        select(func.count())
        .select_from(Bet)
        .where(
            Bet.id.in_(select(participant_subq)),
            Bet.creator_id != user_id,
            Bet.status.in_(active_statuses),
        )
    )
    participant_count = participant_count_result.scalar() or 0

    return creator_count + participant_count
