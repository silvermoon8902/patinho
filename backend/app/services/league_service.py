from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.bet import Bet, BetStatus
from app.models.league import League
from app.models.league_membership import LeagueMembership
from app.models.participation import Participation
from app.models.user import User
from app.schemas.league import LeagueCreate


async def create_league(
    db: AsyncSession, owner_id: UUID, data: LeagueCreate
) -> League:
    """Create a league and auto-add the owner as the first member."""
    league = League(
        owner_id=owner_id,
        name=data.name.strip(),
        description=(data.description or "").strip() or None,
    )
    db.add(league)
    await db.flush()

    membership = LeagueMembership(league_id=league.id, user_id=owner_id)
    db.add(membership)
    await db.flush()

    return await get_league(db, league.id)


async def get_league(db: AsyncSession, league_id: UUID) -> League:
    """Fetch league with memberships + member users eagerly loaded."""
    result = await db.execute(
        select(League)
        .where(League.id == league_id)
        .options(selectinload(League.memberships).selectinload(LeagueMembership.user))
    )
    league = result.scalar_one_or_none()
    if not league:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Liga não encontrada",
        )
    return league


async def get_league_by_code(db: AsyncSession, invite_code: str) -> League:
    """Public lookup by invite code."""
    result = await db.execute(
        select(League)
        .where(League.invite_code == invite_code)
        .options(selectinload(League.memberships).selectinload(LeagueMembership.user))
    )
    league = result.scalar_one_or_none()
    if not league:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Código de convite inválido",
        )
    return league


async def list_user_leagues(
    db: AsyncSession, user_id: UUID
) -> list[League]:
    """Return all leagues where the user is a member, newest first."""
    membership_subq = (
        select(LeagueMembership.league_id)
        .where(LeagueMembership.user_id == user_id)
        .subquery()
    )

    result = await db.execute(
        select(League)
        .where(League.id.in_(select(membership_subq)))
        .options(
            selectinload(League.memberships).selectinload(LeagueMembership.user)
        )
        .order_by(League.created_at.desc())
    )
    return list(result.scalars().all())


async def is_member(db: AsyncSession, league_id: UUID, user_id: UUID) -> bool:
    result = await db.execute(
        select(LeagueMembership).where(
            LeagueMembership.league_id == league_id,
            LeagueMembership.user_id == user_id,
        )
    )
    return result.scalar_one_or_none() is not None


async def invite_to_league(
    db: AsyncSession, league_id: UUID, owner_id: UUID, identifier: str
) -> str:
    """
    Owner invites a user by username OR email.
    Returns a status string: "added" | "already_member" | "user_not_found".
    """
    league = await get_league(db, league_id)
    if league.owner_id != owner_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas o dono da liga pode convidar membros",
        )

    identifier = identifier.strip()
    if not identifier:
        return "user_not_found"

    result = await db.execute(
        select(User).where(
            (User.username == identifier) | (User.email == identifier.lower())
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        return "user_not_found"

    # Already a member?
    existing = await db.execute(
        select(LeagueMembership).where(
            LeagueMembership.league_id == league_id,
            LeagueMembership.user_id == user.id,
        )
    )
    if existing.scalar_one_or_none():
        return "already_member"

    membership = LeagueMembership(league_id=league_id, user_id=user.id)
    db.add(membership)
    await db.flush()
    return "added"


async def join_by_code(
    db: AsyncSession, user_id: UUID, invite_code: str
) -> League:
    """User joins via a shared invite code. No-op if already member."""
    league = await get_league_by_code(db, invite_code.strip())

    existing = await db.execute(
        select(LeagueMembership).where(
            LeagueMembership.league_id == league.id,
            LeagueMembership.user_id == user_id,
        )
    )
    if not existing.scalar_one_or_none():
        membership = LeagueMembership(league_id=league.id, user_id=user_id)
        db.add(membership)
        await db.flush()

    return await get_league(db, league.id)


async def leave_league(
    db: AsyncSession, league_id: UUID, user_id: UUID
) -> None:
    """
    Remove a membership.
    - Non-owners: just delete their membership.
    - Owner: only allowed to leave if they are the only member, which
      effectively deletes the league.
    """
    league = await get_league(db, league_id)

    # Find this user's membership
    result = await db.execute(
        select(LeagueMembership).where(
            LeagueMembership.league_id == league_id,
            LeagueMembership.user_id == user_id,
        )
    )
    membership = result.scalar_one_or_none()
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Você não é membro desta liga",
        )

    if league.owner_id == user_id:
        # Owner leaving — only permitted if they are the sole member.
        if len(league.memberships) > 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "O dono não pode sair enquanto houver outros membros. "
                    "Transfira ou exclua a liga."
                ),
            )
        # Sole owner — delete league entirely (cascade deletes membership).
        await db.delete(league)
        await db.flush()
        return

    await db.delete(membership)
    await db.flush()


async def remove_member(
    db: AsyncSession, league_id: UUID, owner_id: UUID, user_id: UUID
) -> None:
    """Owner removes a member. Owner cannot remove themselves via this path."""
    league = await get_league(db, league_id)
    if league.owner_id != owner_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas o dono da liga pode remover membros",
        )
    if user_id == owner_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O dono não pode se remover. Exclua a liga.",
        )

    result = await db.execute(
        select(LeagueMembership).where(
            LeagueMembership.league_id == league_id,
            LeagueMembership.user_id == user_id,
        )
    )
    membership = result.scalar_one_or_none()
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Membro não encontrado nesta liga",
        )
    await db.delete(membership)
    await db.flush()


async def delete_league(
    db: AsyncSession, league_id: UUID, user_id: UUID
) -> None:
    """
    Owner-only. Reject deletion if there are bets in non-terminal states
    scoped to this league. Otherwise, clear league_id on terminal bets,
    delete memberships, then delete the league.
    """
    league = await get_league(db, league_id)
    if league.owner_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas o dono pode excluir a liga",
        )

    terminal_statuses = [BetStatus.RESOLVED, BetStatus.CANCELLED]
    bets_result = await db.execute(
        select(Bet).where(Bet.league_id == league_id)
    )
    bets = list(bets_result.scalars().all())
    non_terminal = [b for b in bets if b.status not in terminal_statuses]
    if non_terminal:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Não é possível excluir: existem desafios ativos nesta liga"
            ),
        )

    # Detach historical (terminal) bets from the league, then delete.
    for bet in bets:
        bet.league_id = None

    # cascade on membership relationship removes memberships
    await db.delete(league)
    await db.flush()


async def get_league_ranking(
    db: AsyncSession, league_id: UUID
) -> list[dict]:
    """
    Return members ranked by the points they've earned in bets scoped to
    THIS league.

    Ranking is computed from Participation rows whose bet.league_id matches
    this league: a "win" is a participation where the bet is RESOLVED and
    the participant's option is the declared winner. We award 1 point per
    win in v1. total_points here reflects league-local wins, not the user's
    global total_points.

    NOTE: v1 intentionally scopes ranking to this league only. A future
    improvement could weight points differently (e.g. by entry amount).
    """
    league = await get_league(db, league_id)

    # Pull all participations for bets in this league, with joined bet + user.
    result = await db.execute(
        select(Participation, Bet, User)
        .join(Bet, Bet.id == Participation.bet_id)
        .join(User, User.id == Participation.user_id)
        .where(Bet.league_id == league_id)
    )

    # Aggregate per user
    stats: dict[UUID, dict] = {}
    for p, bet, user in result.all():
        entry = stats.setdefault(
            user.id,
            {
                "user_id": user.id,
                "username": user.username,
                "total_points": 0,
                "wins": 0,
                "participations": 0,
            },
        )
        entry["participations"] += 1
        if (
            bet.status == BetStatus.RESOLVED
            and bet.declared_winner_option_id is not None
            and p.bet_option_id == bet.declared_winner_option_id
        ):
            entry["wins"] += 1
            entry["total_points"] += 1

    # Ensure every member appears even with zero activity.
    for membership in league.memberships:
        if membership.user_id not in stats:
            stats[membership.user_id] = {
                "user_id": membership.user_id,
                "username": membership.user.username if membership.user else "",
                "total_points": 0,
                "wins": 0,
                "participations": 0,
            }

    ranked = sorted(
        stats.values(),
        key=lambda e: (e["total_points"], e["wins"], e["participations"]),
        reverse=True,
    )
    return ranked


def build_league_response(league: League) -> dict:
    return {
        "id": league.id,
        "owner_id": league.owner_id,
        "name": league.name,
        "description": league.description,
        "invite_code": league.invite_code,
        "created_at": league.created_at,
        "member_count": len(league.memberships or []),
    }


def build_league_detail(league: League, current_user_id: UUID) -> dict:
    data = build_league_response(league)
    members = []
    is_member_flag = False
    for m in league.memberships or []:
        if m.user_id == current_user_id:
            is_member_flag = True
        members.append(
            {
                "user_id": m.user_id,
                "username": m.user.username if m.user else "",
                "joined_at": m.joined_at,
                "is_owner": m.user_id == league.owner_id,
            }
        )
    data["members"] = members
    data["is_member"] = is_member_flag
    data["is_owner"] = league.owner_id == current_user_id
    return data
