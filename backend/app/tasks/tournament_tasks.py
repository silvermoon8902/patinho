"""
Celery tasks for tournament bets (Bolão da Copa et al.).

- `check_tournament_matches`: every 5 min, find finished fixtures for active
  tournament bets and apply scoring. Also triggers final resolution when the
  tournament's final match is scored.
- `reveal_knockout_fixtures`: lets unlocked KO fixtures become palpite-able
  after the bracket is drawn (no-op today; fixtures appear from the API as
  soon as they're scheduled).
"""
from __future__ import annotations

import asyncio
import logging

from app.celery_app import celery_app

logger = logging.getLogger(__name__)


async def _check_tournament_matches_async() -> int:
    from sqlalchemy import select

    from app.database import async_session_maker
    from app.integrations.api_futebol import api_futebol_client
    from app.models.bet_template import BetTemplate
    from app.models.tournament import TournamentBet, TournamentPalpite
    from app.services import tournament_service

    async with async_session_maker() as db:
        try:
            tb_result = await db.execute(select(TournamentBet))
            tbets = list(tb_result.scalars().all())
            if not tbets:
                return 0

            scored_fixtures = 0
            for tb in tbets:
                if tb.current_phase == "resolved":
                    continue

                # Collect distinct fixture_ids we have palpites for
                p_result = await db.execute(
                    select(TournamentPalpite.fixture_id).where(
                        TournamentPalpite.bet_id == tb.bet_id
                    )
                )
                fixture_ids = {row[0] for row in p_result.all()}
                if not fixture_ids:
                    continue

                # Query results one-by-one (API-Football free tier limitation)
                for fid in fixture_ids:
                    try:
                        result = await api_futebol_client.get_fixture_result(fid)
                    except Exception:
                        logger.exception("Fixture %s fetch failed", fid)
                        continue
                    if not result:
                        continue
                    home = result.get("home_score")
                    away = result.get("away_score")
                    if home is None or away is None:
                        continue
                    scored = await tournament_service.score_fixture_result(
                        db, tb.bet_id, fid, home, away
                    )
                    scored_fixtures += scored

                    # If this fixture is the final and we have a winner, finalize
                    round_name = (result.get("round") or "").lower()
                    if "final" in round_name and "semi" not in round_name:
                        winner = result.get("winner")
                        if winner and winner not in ("Home", "Away"):
                            await tournament_service.score_champion_and_finalize(
                                db, tb.bet_id, winner
                            )

            await db.commit()
            return scored_fixtures
        except Exception:
            await db.rollback()
            logger.exception("check_tournament_matches error")
            raise


async def _reveal_knockout_fixtures_async() -> int:
    """
    Placeholder: with the API-Football schedule, fixtures for KO rounds
    appear automatically once the bracket is drawn. The `list_fixtures_for_bet`
    helper always queries the latest, so no reveal step is needed — it's
    driven by what the API exposes.
    """
    return 0


@celery_app.task(name="app.tasks.tournament.check_tournament_matches")
def check_tournament_matches() -> int:
    return asyncio.run(_check_tournament_matches_async())


@celery_app.task(name="app.tasks.tournament.reveal_knockout_fixtures")
def reveal_knockout_fixtures() -> int:
    return asyncio.run(_reveal_knockout_fixtures_async())
