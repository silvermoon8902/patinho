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
from app.models.league_membership import LeagueMembership
from app.models.participation import Participation
from app.schemas.bet import BetCreate, BetJoin
from app.services import wallet_service

# Draw label used for football match_winner template. Kept as a module-level
# constant so resolve_sports_bet can match it against the fixture result.
DRAW_LABEL = "Empate"


async def _ensure_member_of_league(
    db: AsyncSession, user_id: UUID, league_id: UUID | None
) -> None:
    """Validate that user is a member of the target league (if provided)."""
    if league_id is None:
        return
    result = await db.execute(
        select(LeagueMembership).where(
            LeagueMembership.league_id == league_id,
            LeagueMembership.user_id == user_id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não é membro desta liga",
        )


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

    await _ensure_member_of_league(db, user_id, data.league_id)

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
        league_id=data.league_id,
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
    template: str,
    entry_amount: Decimal,
    max_participants: int,
    fixture_data: dict | None = None,
    race_data: dict | None = None,
    driver_names: list[str] | None = None,
    tennis_data: dict | None = None,
    league_id: UUID | None = None,
) -> Bet:
    """
    Create a sport bet wired to an external API event.

    Dispatches by template:
      - match_winner (football): options = [home, DRAW_LABEL, away]
      - exact_score (football): options = common scorelines + "Outro"
      - f1_winner (F1): options = selected subset of drivers

    For all templates the bet is tagged with resolution_type=AUTO_API
    plus sports_match_id so the existing Celery pipeline can
    auto-resolve it. closes_at is forced to the event start time.
    """
    active_count = await get_active_bet_count(db, user_id)
    if active_count >= 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum of 10 active bets reached",
        )

    await _ensure_member_of_league(db, user_id, league_id)

    title: str
    options: list[str]
    closes_at: datetime
    sports_match_id: str
    category: str
    description_parts: list[str] = []

    if template == "match_winner":
        if not fixture_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Dados da partida ausentes",
            )
        home = fixture_data["home_team"]
        away = fixture_data["away_team"]
        title = f"{home} vs {away}"
        options = [home, DRAW_LABEL, away]
        closes_at = fixture_data["kickoff_at"]
        sports_match_id = str(fixture_data["fixture_id"])
        category = "football"
        if fixture_data.get("league_name"):
            description_parts.append(fixture_data["league_name"])

    elif template == "exact_score":
        if not fixture_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Dados da partida ausentes",
            )
        home = fixture_data["home_team"]
        away = fixture_data["away_team"]
        title = f"Placar: {home} vs {away}"
        options = [
            "0x0",
            "1x0",
            "0x1",
            "1x1",
            "2x0",
            "0x2",
            "2x1",
            "1x2",
            "Outro",
        ]
        closes_at = fixture_data["kickoff_at"]
        sports_match_id = str(fixture_data["fixture_id"])
        category = "football"
        if fixture_data.get("league_name"):
            description_parts.append(fixture_data["league_name"])

    elif template == "tennis_winner":
        if not tennis_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Dados da partida ausentes",
            )
        player1 = tennis_data.get("player1_name")
        player2 = tennis_data.get("player2_name")
        if not player1 or not player2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Dados dos jogadores incompletos",
            )
        title = f"{player1} vs {player2}"
        options = [player1, player2]
        closes_at = tennis_data["date"]
        sports_match_id = str(tennis_data["match_id"])
        category = "tennis"
        tour = tennis_data.get("tour") or ""
        if tour:
            description_parts.append(f"Tênis {tour}")
        else:
            description_parts.append("Tênis")

    elif template == "f1_winner":
        if not race_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Dados da corrida ausentes",
            )
        if not driver_names or len(driver_names) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Informe pelo menos 2 pilotos",
            )
        if len(driver_names) > 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Máximo de 10 pilotos",
            )
        competition = race_data.get("competition_name") or "Corrida"
        circuit = race_data.get("circuit_name") or ""
        if circuit:
            title = f"Vencedor: {competition} - {circuit}"
        else:
            title = f"Vencedor: {competition}"
        options = list(driver_names)
        closes_at = race_data["date"]
        sports_match_id = str(race_data["race_id"])
        category = "f1"
        if competition:
            description_parts.append(competition)

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Template de aposta não suportado: {template}",
        )

    if closes_at.tzinfo is None:
        closes_at = closes_at.replace(tzinfo=timezone.utc)

    if closes_at <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O evento já começou ou terminou",
        )

    # Defensive dedup while preserving order
    seen: set[str] = set()
    unique_labels: list[str] = []
    for label in options:
        label = label.strip()
        if not label:
            continue
        if label not in seen:
            seen.add(label)
            unique_labels.append(label)
    if len(unique_labels) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não foi possível gerar opções válidas para este evento",
        )

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
        category=category,
        resolution_type=ResolutionType.AUTO_API,
        status=BetStatus.OPEN,
        entry_amount=entry_amount,
        max_participants=max_participants,
        sports_match_id=sports_match_id,
        template=template,
        league_id=league_id,
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
    league_id: UUID | None = None,
) -> list[Bet]:
    """
    List bets where user is creator or participant.

    If league_id is provided, restrict to bets scoped to that league AND
    require the caller to be a member of that league (403 otherwise).
    """
    # When filtering by league, the caller must be a member.
    if league_id is not None:
        await _ensure_member_of_league(db, user_id, league_id)

    # Get bet IDs where user participates
    participation_subq = (
        select(Participation.bet_id)
        .where(Participation.user_id == user_id)
        .subquery()
    )

    if league_id is not None:
        # All league members can see every bet in that league.
        base_where = Bet.league_id == league_id
    else:
        base_where = (Bet.creator_id == user_id) | (
            Bet.id.in_(select(participation_subq))
        )

    query = (
        select(Bet)
        .where(base_where)
        .options(
            selectinload(Bet.options),
            selectinload(Bet.participations),
        )
        .order_by(Bet.created_at.desc())
        .offset(skip)
        .limit(limit)
    )

    if status_filter:
        # Pseudo-filter "active" matches every status that still requires
        # *someone's* attention (creator declaration, participant accept,
        # voting). The "Ativas" tab on the frontend uses this so creators
        # don't lose track of locked bets waiting on them.
        if status_filter == "active":
            query = query.where(
                Bet.status.in_([
                    BetStatus.OPEN,
                    BetStatus.LOCKED,
                    BetStatus.PENDING_CONFIRMATION,
                    BetStatus.VOTING,
                    BetStatus.DISPUTED,
                ])
            )
        else:
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
