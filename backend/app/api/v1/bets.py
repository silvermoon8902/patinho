from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.integrations.api_f1 import api_f1_client
from app.integrations.api_football import api_football_client
from app.integrations.api_tennis import api_tennis_client
from app.models.bet import Bet
from app.models.league_membership import LeagueMembership
from app.models.participation import Participation
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
    EmailInviteRequest,
    EmailInviteResponse,
    ParticipationResponse,
    VoteCountResponse,
    VoteRequest,
)
from app.schemas.payment import PaymentResponse
from app.schemas.sports import BET_TEMPLATES, SportBetCreate
from app.services import (
    bet_service,
    declare_service,
    direct_join_service,
    dispute_service,
    email_service,
    league_service,
    voting_service,
)
from app.services.auth_service import (
    get_current_active_user,
    get_current_user_optional,
)

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
        "league_id": bet.league_id,
        "template": bet.template,
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
    # Per-user rate limit: 15 bets/hour. Stops accidental loops and
    # outright spam without affecting normal use (5–10/day).
    from app.utils.rate_limit import enforce_user_rate_limit

    await enforce_user_rate_limit(
        user.id,
        bucket="create_bet",
        limit=15,
        window_seconds=3600,
        detail="Você criou muitos desafios em pouco tempo. Tente novamente em uma hora.",
    )
    bet = await bet_service.create_bet(db, user.id, data)
    from app.utils import funnel
    funnel.track(
        "bet_created",
        user_id=user.id,
        bet_id=str(bet.id),
        category=data.category,
        resolution_type=data.resolution_type,
        entry_amount=str(data.entry_amount),
    )
    return _build_bet_response(bet)


@router.post("/sport", response_model=BetResponse, status_code=201)
async def create_sport_bet(
    data: SportBetCreate,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a sport bet wired to an external event.

    Dispatches by template:
      - match_winner / exact_score (football): requires fixture_id,
        we fetch kickoff + team names from API-Football.
      - f1_winner: requires race_id + driver_names, we fetch race
        metadata (date/circuit/competition) from API-Formula-1.
    """
    template_meta = BET_TEMPLATES.get(data.template)
    if not template_meta:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Template de aposta não suportado: {data.template}",
        )

    sport = template_meta.get("sport")

    if sport == "football":
        if not data.fixture_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="É necessário escolher uma partida",
            )

        fixtures = await api_football_client.get_fixtures([data.fixture_id])
        if not fixtures:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Partida não encontrada no API-Football",
            )

        raw = fixtures[0]
        fixture = raw.get("fixture", {}) or {}
        teams = raw.get("teams", {}) or {}
        league = raw.get("league", {}) or {}

        home_name = (teams.get("home") or {}).get("name")
        away_name = (teams.get("away") or {}).get("name")
        raw_date = fixture.get("date")

        if not home_name or not away_name or not raw_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Dados da partida incompletos",
            )

        try:
            kickoff_at = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Data da partida inválida",
            )

        if kickoff_at.tzinfo is None:
            kickoff_at = kickoff_at.replace(tzinfo=timezone.utc)

        if kickoff_at <= datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Esta partida já começou ou terminou",
            )

        bet = await bet_service.create_sport_bet(
            db,
            user.id,
            template=data.template,
            entry_amount=data.entry_amount,
            max_participants=data.max_participants,
            fixture_data={
                "fixture_id": str(data.fixture_id),
                "home_team": home_name,
                "away_team": away_name,
                "kickoff_at": kickoff_at,
                "league_name": league.get("name"),
            },
            league_id=data.league_id,
        )
        return _build_bet_response(bet)

    if sport == "f1":
        if not data.race_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="É necessário escolher uma corrida",
            )

        race = await api_f1_client.get_race(data.race_id)
        if not race:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Corrida não encontrada no API-Formula-1",
            )

        raw_date = race.get("date")
        if not raw_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Data da corrida indisponível",
            )

        try:
            race_date = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Data da corrida inválida",
            )

        if race_date.tzinfo is None:
            race_date = race_date.replace(tzinfo=timezone.utc)

        if race_date <= datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Esta corrida já começou ou terminou",
            )

        circuit = race.get("circuit") or {}
        competition = race.get("competition") or {}

        bet = await bet_service.create_sport_bet(
            db,
            user.id,
            template=data.template,
            entry_amount=data.entry_amount,
            max_participants=data.max_participants,
            race_data={
                "race_id": str(data.race_id),
                "date": race_date,
                "circuit_name": circuit.get("name") or "",
                "competition_name": competition.get("name") or "",
            },
            driver_names=data.driver_names,
            league_id=data.league_id,
        )
        return _build_bet_response(bet)

    if sport == "tennis":
        if not data.tennis_match_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="É necessário escolher uma partida de tênis",
            )

        match = await api_tennis_client.get_match(data.tennis_match_id)
        if not match:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Partida não encontrada no API-Tennis",
            )

        # Extract player names and date using the client's helpers
        p1, p2 = api_tennis_client._extract_player_names(match)
        raw_date = api_tennis_client._extract_start_date(match)
        tour = api_tennis_client._extract_tour(match)

        if not p1 or not p2 or not raw_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Dados da partida de tênis incompletos",
            )

        try:
            match_date = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Data da partida inválida",
            )

        if match_date.tzinfo is None:
            match_date = match_date.replace(tzinfo=timezone.utc)

        if match_date <= datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Esta partida já começou ou terminou",
            )

        bet = await bet_service.create_sport_bet(
            db,
            user.id,
            template=data.template,
            entry_amount=data.entry_amount,
            max_participants=data.max_participants,
            tennis_data={
                "match_id": str(data.tennis_match_id),
                "date": match_date,
                "tour": tour,
                "player1_name": p1,
                "player2_name": p2,
            },
            league_id=data.league_id,
        )
        return _build_bet_response(bet)

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Esporte não suportado: {sport}",
    )


@router.get("", response_model=list[BetResponse])
async def list_user_bets(
    status: str | None = Query(default=None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    league_id: UUID | None = Query(default=None),
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    bets = await bet_service.get_user_bets(
        db, user.id, status, skip, limit, league_id=league_id
    )
    return [_build_bet_response(b) for b in bets]


@router.get("/invite/{invite_token}", response_model=BetResponse)
async def get_bet_by_invite(
    invite_token: str,
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
):
    bet = await bet_service.get_bet_by_invite(db, invite_token)

    # League-scoped bets require an authenticated member to preview.
    # Hide their existence from everyone else (return 404) so leaked
    # invite links don't expose private bet contents.
    if bet.league_id is not None:
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bet not found",
            )
        if bet.creator_id != user.id and not await league_service.is_member(
            db, bet.league_id, user.id
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bet not found",
            )

    return _build_bet_response(bet)


@router.get("/{bet_id}", response_model=BetDetailResponse)
async def get_bet_detail(
    bet_id: UUID,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    bet = await bet_service.get_bet(db, bet_id)
    await league_service.require_bet_access(db, bet, user.id)
    return _build_detail_response(bet)


@router.delete("/{bet_id}", status_code=204)
async def delete_bet(
    bet_id: UUID,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    await bet_service.delete_bet(db, user.id, bet_id)


@router.post("/{bet_id}/join", response_model=ParticipationResponse)
async def join_bet(
    bet_id: UUID,
    data: BetJoin,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    bet = await bet_service.get_bet(db, bet_id)
    await league_service.require_bet_access(db, bet, user.id)
    participation = await bet_service.join_bet(db, user.id, bet_id, data)
    from app.utils import funnel
    funnel.track("bet_joined", user_id=user.id, bet_id=str(bet_id))
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
    bet = await bet_service.get_bet(db, bet_id)
    await league_service.require_bet_access(db, bet, user.id)
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
    return await declare_service.accept_result(db, bet_id, user.id)


@router.get("/{bet_id}/contestations", response_model=list[ContestationResponse])
async def list_contestations(
    bet_id: UUID,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    contestations = await declare_service.get_contestations(db, bet_id)
    return [ContestationResponse.model_validate(c) for c in contestations]


def _format_brl(amount) -> str:
    try:
        return "R$ " + f"{float(amount):.2f}".replace(".", ",")
    except (ValueError, TypeError):
        return f"R$ {amount}"


@router.post("/{bet_id}/email-invite", response_model=EmailInviteResponse)
async def send_email_invites(
    bet_id: UUID,
    data: EmailInviteRequest,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Send bet invite emails to up to 10 addresses.

    Caller must be the bet creator or an existing participant.
    Returns a per-email status map; individual failures do not abort the
    request.
    """
    bet = await bet_service.get_bet(db, bet_id)

    # Authorization: creator or participant
    is_creator = bet.creator_id == user.id
    is_participant = any(
        p.user_id == user.id for p in (bet.participations or [])
    )
    if not (is_creator or is_participant):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas o criador ou um participante pode enviar convites",
        )

    invite_url = f"{settings.APP_URL.rstrip('/')}/invite/{bet.invite_token}"
    entry_amount_str = _format_brl(bet.entry_amount)
    inviter_name = user.username or "Um amigo"
    subject = f"{inviter_name} te convidou para o desafio \"{bet.title}\" no Patinho"

    # Build set of emails that already know about this bet
    participant_user_ids = {p.user_id for p in (bet.participations or [])}
    participant_user_ids.add(bet.creator_id)

    known_emails_lower: set[str] = set()
    if participant_user_ids:
        existing_users = await db.execute(
            select(User).where(User.id.in_(participant_user_ids))
        )
        for u in existing_users.scalars().all():
            if u.email:
                known_emails_lower.add(u.email.lower())

    # For league-scoped bets, only allow inviting existing league members.
    # Non-members would click the link and be blocked from joining, so the
    # email would just be misleading. Require league-add-first workflow.
    league_member_emails_lower: set[str] | None = None
    if bet.league_id is not None:
        member_rows = await db.execute(
            select(User.email)
            .join(LeagueMembership, LeagueMembership.user_id == User.id)
            .where(LeagueMembership.league_id == bet.league_id)
        )
        league_member_emails_lower = {
            (e or "").lower() for (e,) in member_rows.all() if e
        }

    results: dict[str, str] = {}
    # Normalize dedupe the requested emails while preserving order
    seen_emails: set[str] = set()
    unique_emails: list[str] = []
    for raw_email in data.emails:
        email_str = str(raw_email).strip()
        if not email_str:
            continue
        key = email_str.lower()
        if key in seen_emails:
            continue
        seen_emails.add(key)
        unique_emails.append(email_str)

    for email in unique_emails:
        if email.lower() in known_emails_lower:
            results[email] = "skipped"
            continue

        if (
            league_member_emails_lower is not None
            and email.lower() not in league_member_emails_lower
        ):
            results[email] = "not_in_league"
            continue

        try:
            html, text = email_service.render_bet_invite(
                inviter_name=inviter_name,
                bet_title=bet.title,
                invite_url=invite_url,
                entry_amount=entry_amount_str,
            )
            sent = await email_service.send_email(
                to=email,
                subject=subject,
                html=html,
                text=text,
            )
            results[email] = "sent" if sent else "failed"
        except Exception:
            results[email] = "failed"

    return EmailInviteResponse(results=results)
