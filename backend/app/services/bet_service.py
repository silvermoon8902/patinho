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

# Draw label used for football match_winner template. Kept as a module-level
# constant so resolve_sports_bet can match it against the fixture result.
DRAW_LABEL = "Empate"


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
        entry_amount=data.entry_amount,
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


async def create_sport_bet(
    db: AsyncSession,
    user_id: UUID,
    *,
    fixture_id: str,
    home_team: str,
    away_team: str,
    kickoff_at: datetime,
    league_name: str | None,
    template: str,
    entry_amount: Decimal,
    max_participants: int,
) -> Bet:
    """
    Create a sport bet wired to an API-Football fixture.

    The options are pre-computed from the template (today only
    'match_winner' is supported) and the closing time is forced to the
    fixture kickoff so entries close when the match starts. The bet is
    tagged with resolution_type=AUTO_API and sports_match_id so the
    existing Celery resolution pipeline can auto-resolve it.
    """
    active_count = await get_active_bet_count(db, user_id)
    if active_count >= 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum of 10 active bets reached",
        )

    if kickoff_at.tzinfo is None:
        closes_at = kickoff_at.replace(tzinfo=timezone.utc)
    else:
        closes_at = kickoff_at

    if closes_at <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Esta partida já começou ou terminou",
        )

    if template == "match_winner":
        option_labels = [home_team, DRAW_LABEL, away_team]
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Template de aposta não suportado: {template}",
        )

    # Defensive dedup in case the two team names happen to collide
    seen: set[str] = set()
    unique_labels: list[str] = []
    for label in option_labels:
        if label not in seen:
            seen.add(label)
            unique_labels.append(label)
    if len(unique_labels) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não foi possível gerar opções válidas para esta partida",
        )

    title = f"{home_team} vs {away_team}"

    description_parts: list[str] = []
    if league_name:
        description_parts.append(league_name)
    description_parts.append(
        closes_at.astimezone(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
    )
    description = " - ".join(description_parts)

    invite_token = secrets.token_urlsafe(16)

    bet = Bet(
        creator_id=user_id,
        title=title,
        description=description,
        invite_token=invite_token,
        category="football",
        resolution_type=ResolutionType.AUTO_API,
        status=BetStatus.OPEN,
        entry_amount=entry_amount,
        max_participants=max_participants,
        sports_match_id=str(fixture_id),
        closes_at=closes_at,
    )
    db.add(bet)
    await db.flush()

    for label in unique_labels:
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

    # Validate option belongs to this bet
    option_ids = {opt.id for opt in bet.options}
    if data.bet_option_id not in option_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid bet option for this bet",
        )

    # Amount is fixed by the bet
    amount = bet.entry_amount

    # Lock funds in wallet
    await wallet_service.lock_funds(db, user_id, amount, bet_id)

    participation = Participation(
        bet_id=bet_id,
        user_id=user_id,
        bet_option_id=data.bet_option_id,
        amount=amount,
    )
    db.add(participation)
    await db.flush()

    return participation


async def delete_bet(db: AsyncSession, user_id: UUID, bet_id: UUID) -> None:
    """
    Delete a bet. Only allowed when:
    - User is the creator
    - Bet is still open
    - At most 1 participant (i.e., only the creator joined, or nobody)

    If the creator is a participant, their funds are unlocked before deletion.
    """
    bet = await get_bet(db, bet_id)

    if bet.creator_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas o criador pode excluir o desafio",
        )

    if bet.status != BetStatus.OPEN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Só é possível excluir desafios abertos",
        )

    # Count participations
    part_result = await db.execute(
        select(Participation).where(Participation.bet_id == bet_id)
    )
    participations = list(part_result.scalars().all())

    if len(participations) > 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é possível excluir: outros participantes já entraram",
        )

    # Unlock funds for any participant (should only be the creator if any)
    from app.services import wallet_service
    for p in participations:
        await wallet_service.unlock_funds(db, p.user_id, p.amount, bet_id)

    # Delete participations then bet options then bet
    for p in participations:
        await db.delete(p)

    opts_result = await db.execute(
        select(BetOption).where(BetOption.bet_id == bet_id)
    )
    for opt in opts_result.scalars().all():
        await db.delete(opt)

    await db.delete(bet)
    await db.flush()


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
