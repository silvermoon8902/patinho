"""
Tournament bet service.

Handles the Bolão da Copa lifecycle:
  - Creating a tournament bet from a registered template
  - Loading fixtures and existing palpites for a user
  - Bulk-submitting palpites (with lock-window enforcement)
  - Recording the champion prediction
  - Scoring fixtures as they finish (group/knockout scoring rules)
  - Computing the live leaderboard
  - Final prize distribution when the tournament concludes
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bet import Bet, BetStatus, ResolutionType
from app.models.bet_template import BetTemplate
from app.models.tournament import (
    TournamentBet,
    TournamentChampionPalpite,
    TournamentPalpite,
)
from app.models.user import User
from app.services.distribution_service import distribute_prizes

logger = logging.getLogger(__name__)

# Knockout phases ordered — determines scoring multiplier
KNOCKOUT_PHASES = {"ko_16", "ko_8", "ko_4", "semifinal", "ko_2", "final"}


async def get_template_by_code(db: AsyncSession, code: str) -> BetTemplate:
    result = await db.execute(select(BetTemplate).where(BetTemplate.code == code))
    tmpl = result.scalar_one_or_none()
    if not tmpl:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{code}' não encontrado",
        )
    if not tmpl.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Template '{code}' está desativado",
        )
    return tmpl


async def create_tournament_bet(
    db: AsyncSession,
    user_id: UUID,
    template_code: str,
    entry_amount: Decimal,
    max_participants: int,
) -> Bet:
    """Create a `bet` + `tournament_bet` row from a template."""
    tmpl = await get_template_by_code(db, template_code)
    if tmpl.kind != "tournament":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este template não é de torneio",
        )

    selector = tmpl.event_selector or {}
    tournament_id = selector.get("tournament_id")
    if not tournament_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Template sem tournament_id configurado",
        )

    # closes_at = far future; tournaments resolve on their own events
    closes_at = datetime.now(timezone.utc) + timedelta(days=365)

    import secrets

    bet = Bet(
        creator_id=user_id,
        title=tmpl.name,
        description=tmpl.description,
        invite_token=secrets.token_urlsafe(16)[:32],
        category="football",
        resolution_type=ResolutionType.AUTO_API,
        status=BetStatus.OPEN,
        entry_amount=entry_amount,
        max_participants=max_participants,
        closes_at=closes_at,
        template=template_code,
    )
    db.add(bet)
    await db.flush()

    tb = TournamentBet(
        bet_id=bet.id,
        template_id=tmpl.id,
        tournament_id=tournament_id,
        current_phase="group",
    )
    db.add(tb)
    await db.flush()

    logger.info(
        "Created tournament bet %s (%s) from template %s",
        bet.id, tournament_id, template_code,
    )
    return bet


async def list_fixtures_for_bet(
    db: AsyncSession, bet_id: UUID
) -> list[dict[str, Any]]:
    """
    Fetch the list of fixtures for the tournament this bet is scoped to,
    joined with the user's existing palpites.

    Today: returns cached fixtures from the API-Football provider. When
    the draw for KO phases happens, the Celery task `reveal_knockout_fixtures`
    adds new rows that become palpite-able.
    """
    from app.integrations.api_football import api_football_client

    tb_result = await db.execute(
        select(TournamentBet).where(TournamentBet.bet_id == bet_id)
    )
    tb = tb_result.scalar_one_or_none()
    if not tb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bet não é um torneio registrado",
        )

    tmpl_result = await db.execute(
        select(BetTemplate).where(BetTemplate.id == tb.template_id)
    )
    tmpl = tmpl_result.scalar_one()
    selector = tmpl.event_selector or {}
    league_id = selector.get("api_league_id", 1)
    season = selector.get("api_season", 2026)

    try:
        raw, _tag = await api_football_client.list_upcoming_fixtures(league_id, season)
    except Exception:
        logger.exception("Failed to fetch tournament fixtures")
        raw = []

    fixtures: list[dict[str, Any]] = []
    for f in raw or []:
        fix = (f.get("fixture") or {})
        teams = (f.get("teams") or {})
        fid = str(fix.get("id") or "")
        if not fid:
            continue
        raw_date = fix.get("date")
        try:
            kickoff = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
        except Exception:
            continue
        if kickoff.tzinfo is None:
            kickoff = kickoff.replace(tzinfo=timezone.utc)
        lock_minutes = (tmpl.palpite_schema or {}).get("lock_minutes_before_kickoff", 10)
        locks_at = kickoff - timedelta(minutes=lock_minutes)
        home = (teams.get("home") or {})
        away = (teams.get("away") or {})
        fixtures.append({
            "fixture_id": fid,
            "phase": _phase_from_round((f.get("league") or {}).get("round", "")),
            "kickoff_at": kickoff.isoformat(),
            "locks_at": locks_at.isoformat(),
            "home_team": home.get("name"),
            "away_team": away.get("name"),
            "home_logo": home.get("logo"),
            "away_logo": away.get("logo"),
        })
    return fixtures


def _phase_from_round(round_str: str) -> str:
    s = (round_str or "").lower()
    if "group" in s or "grupo" in s:
        return "group"
    if "round of 16" in s or "oitavas" in s:
        return "ko_16"
    if "quarter" in s or "quartas" in s:
        return "ko_8"
    if "semi" in s:
        return "semifinal"
    if "final" in s:
        return "final"
    return "group"


async def get_user_palpites(
    db: AsyncSession, bet_id: UUID, user_id: UUID
) -> dict[str, TournamentPalpite]:
    result = await db.execute(
        select(TournamentPalpite).where(
            TournamentPalpite.bet_id == bet_id,
            TournamentPalpite.user_id == user_id,
        )
    )
    return {p.fixture_id: p for p in result.scalars().all()}


async def submit_palpites_bulk(
    db: AsyncSession,
    bet_id: UUID,
    user_id: UUID,
    palpites: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Accept or update multiple palpites at once.

    Each palpite dict: { fixture_id, home_score, away_score, phase, locks_at (ISO) }.
    Rejects any whose lock window has already passed.
    """
    # Verify user is a participant
    from app.models.participation import Participation
    part_result = await db.execute(
        select(Participation).where(
            Participation.bet_id == bet_id,
            Participation.user_id == user_id,
        )
    )
    if part_result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas participantes podem palpitar",
        )

    existing = await get_user_palpites(db, bet_id, user_id)
    now = datetime.now(timezone.utc)
    saved = 0
    locked = 0
    for p in palpites:
        fid = str(p.get("fixture_id") or "")
        if not fid:
            continue
        try:
            home_score = int(p.get("home_score"))
            away_score = int(p.get("away_score"))
        except (TypeError, ValueError):
            continue
        phase = p.get("phase") or "group"
        locks_at_raw = p.get("locks_at")
        locks_at = None
        if locks_at_raw:
            try:
                locks_at = datetime.fromisoformat(locks_at_raw.replace("Z", "+00:00"))
                if locks_at.tzinfo is None:
                    locks_at = locks_at.replace(tzinfo=timezone.utc)
            except Exception:
                locks_at = None

        if locks_at and locks_at <= now:
            locked += 1
            continue

        if fid in existing:
            row = existing[fid]
            row.predicted_home_score = home_score
            row.predicted_away_score = away_score
            row.phase = phase
            if locks_at:
                row.locks_at = locks_at
        else:
            row = TournamentPalpite(
                bet_id=bet_id,
                user_id=user_id,
                fixture_id=fid,
                phase=phase,
                predicted_home_score=home_score,
                predicted_away_score=away_score,
                locks_at=locks_at,
            )
            db.add(row)
        saved += 1

    await db.flush()
    return {"saved": saved, "rejected_locked": locked}


async def submit_champion_palpite(
    db: AsyncSession, bet_id: UUID, user_id: UUID, team_name: str
) -> TournamentChampionPalpite:
    # Verify user is a participant
    from app.models.participation import Participation
    part_result = await db.execute(
        select(Participation).where(
            Participation.bet_id == bet_id,
            Participation.user_id == user_id,
        )
    )
    if part_result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas participantes podem palpitar",
        )

    existing_result = await db.execute(
        select(TournamentChampionPalpite).where(
            TournamentChampionPalpite.bet_id == bet_id,
            TournamentChampionPalpite.user_id == user_id,
        )
    )
    existing = existing_result.scalar_one_or_none()
    if existing:
        existing.predicted_champion = team_name
        await db.flush()
        return existing

    row = TournamentChampionPalpite(
        bet_id=bet_id, user_id=user_id, predicted_champion=team_name
    )
    db.add(row)
    await db.flush()
    return row


async def get_ranking(
    db: AsyncSession, bet_id: UUID
) -> list[dict[str, Any]]:
    """Sum points_earned per user from palpites + champion palpite. Returns sorted leaderboard."""
    # Per-fixture points
    result = await db.execute(
        select(TournamentPalpite).where(TournamentPalpite.bet_id == bet_id)
    )
    palpites = list(result.scalars().all())
    totals: dict[UUID, int] = {}
    for p in palpites:
        totals[p.user_id] = totals.get(p.user_id, 0) + (p.points_earned or 0)

    # Champion points (only granted when tournament ends)
    champ_result = await db.execute(
        select(TournamentChampionPalpite).where(
            TournamentChampionPalpite.bet_id == bet_id
        )
    )
    for c in champ_result.scalars().all():
        totals[c.user_id] = totals.get(c.user_id, 0) + (c.points_earned or 0)

    # Load usernames
    if not totals:
        return []
    users_result = await db.execute(
        select(User).where(User.id.in_(list(totals.keys())))
    )
    users_map = {u.id: u for u in users_result.scalars().all()}

    rows = [
        {
            "user_id": str(uid),
            "username": users_map[uid].username if uid in users_map else "???",
            "points": pts,
        }
        for uid, pts in totals.items()
    ]
    rows.sort(key=lambda r: r["points"], reverse=True)
    for i, r in enumerate(rows, start=1):
        r["rank"] = i
    return rows


async def score_fixture_result(
    db: AsyncSession,
    bet_id: UUID,
    fixture_id: str,
    actual_home_score: int,
    actual_away_score: int,
) -> int:
    """
    Apply scoring rules to all palpites for a given fixture within a tournament bet.
    Returns number of palpites scored.
    """
    tb_result = await db.execute(
        select(TournamentBet).where(TournamentBet.bet_id == bet_id)
    )
    tb = tb_result.scalar_one_or_none()
    if not tb:
        return 0

    tmpl_result = await db.execute(
        select(BetTemplate).where(BetTemplate.id == tb.template_id)
    )
    tmpl = tmpl_result.scalar_one()
    rules = tmpl.scoring_rules or {}

    result = await db.execute(
        select(TournamentPalpite).where(
            TournamentPalpite.bet_id == bet_id,
            TournamentPalpite.fixture_id == str(fixture_id),
        )
    )
    palpites = list(result.scalars().all())

    actual_winner = "home" if actual_home_score > actual_away_score else (
        "away" if actual_away_score > actual_home_score else "draw"
    )

    count = 0
    for p in palpites:
        if p.predicted_home_score is None or p.predicted_away_score is None:
            continue
        predicted_winner = (
            "home" if p.predicted_home_score > p.predicted_away_score else (
                "away" if p.predicted_away_score > p.predicted_home_score else "draw"
            )
        )
        phase_rules = rules.get(
            "knockout" if p.phase in KNOCKOUT_PHASES else "group_stage", {}
        )
        exact_pts = int(phase_rules.get("exact_score", 6))
        winner_pts = int(phase_rules.get("winner", 3))
        if (
            p.predicted_home_score == actual_home_score
            and p.predicted_away_score == actual_away_score
        ):
            p.points_earned = exact_pts
        elif predicted_winner == actual_winner:
            p.points_earned = winner_pts
        else:
            p.points_earned = 0
        count += 1

    await db.flush()
    return count


async def score_champion_and_finalize(
    db: AsyncSession, bet_id: UUID, champion_team_name: str
) -> None:
    """
    Called when the final match resolves. Awards champion points and
    triggers prize distribution based on the live ranking.
    """
    tb_result = await db.execute(
        select(TournamentBet).where(TournamentBet.bet_id == bet_id)
    )
    tb = tb_result.scalar_one_or_none()
    if not tb:
        return

    tmpl_result = await db.execute(
        select(BetTemplate).where(BetTemplate.id == tb.template_id)
    )
    tmpl = tmpl_result.scalar_one()
    rules = tmpl.scoring_rules or {}
    champion_pts = int(rules.get("champion", 30))

    champ_result = await db.execute(
        select(TournamentChampionPalpite).where(
            TournamentChampionPalpite.bet_id == bet_id
        )
    )
    for c in champ_result.scalars().all():
        if c.predicted_champion.strip().lower() == (champion_team_name or "").strip().lower():
            c.points_earned = champion_pts
        else:
            c.points_earned = 0

    tb.current_phase = "resolved"
    await db.flush()

    # Determine the top-scoring bet option among the bet's options. Tournament
    # bets don't have traditional options; distribute_prizes expects an
    # option_id, so we create a synthetic "winners" option and wire it up.
    ranking = await get_ranking(db, bet_id)
    if not ranking:
        return

    top_points = ranking[0]["points"]
    winner_user_ids = [
        UUID(r["user_id"]) for r in ranking if r["points"] == top_points
    ]

    # Ensure the bet has a single "winners" option; mark every winner's
    # participation to this option, then call distribute_prizes.
    from app.models.bet_option import BetOption
    from app.models.participation import Participation

    opts_result = await db.execute(
        select(BetOption).where(BetOption.bet_id == bet_id)
    )
    opts = list(opts_result.scalars().all())
    if opts:
        winners_opt = opts[0]
    else:
        winners_opt = BetOption(bet_id=bet_id, label="Vencedor(es) do bolão")
        db.add(winners_opt)
        await db.flush()

    parts_result = await db.execute(
        select(Participation).where(Participation.bet_id == bet_id)
    )
    for p in parts_result.scalars().all():
        if p.user_id in winner_user_ids:
            p.bet_option_id = winners_opt.id
    await db.flush()

    await distribute_prizes(db, bet_id, winners_opt.id)
    logger.info(
        "Tournament bet %s resolved: %d winner(s) tied at %d points",
        bet_id, len(winner_user_ids), top_points,
    )
