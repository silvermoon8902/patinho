import logging

from fastapi import APIRouter, Query

from app.integrations.api_football import (
    SUPPORTED_LEAGUES,
    api_football_client,
)
from app.schemas.sports import LEAGUE_LABELS, FixtureResponse, LeagueResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["sports"])


@router.get("/leagues", response_model=list[LeagueResponse])
async def list_leagues() -> list[LeagueResponse]:
    """Return the list of supported leagues with display labels."""
    return [
        LeagueResponse(
            id=key,
            name=LEAGUE_LABELS.get(key, key),
            api_id=api_id,
        )
        for key, api_id in SUPPORTED_LEAGUES.items()
    ]


@router.get(
    "/leagues/{league_id}/fixtures",
    response_model=list[FixtureResponse],
)
async def list_league_fixtures(
    league_id: str,
    season: int = Query(default=2026, ge=2020, le=2099),
) -> list[FixtureResponse]:
    """
    List upcoming fixtures for the given league.

    Gracefully returns [] when:
      - the league is unknown
      - the upstream API fails
      - no upcoming fixtures are found
    """
    api_id = SUPPORTED_LEAGUES.get(league_id)
    if api_id is None:
        return []

    try:
        raw_fixtures = await api_football_client.list_upcoming_fixtures(
            api_id, season
        )
    except Exception:
        logger.exception(
            "Failed to list upcoming fixtures for league %s/%s",
            league_id,
            season,
        )
        return []

    fixtures: list[FixtureResponse] = []
    for raw in raw_fixtures[:20]:
        fixture = raw.get("fixture", {}) or {}
        teams = raw.get("teams", {}) or {}
        home = teams.get("home", {}) or {}
        away = teams.get("away", {}) or {}
        league = raw.get("league", {}) or {}

        fid = fixture.get("id")
        date = fixture.get("date")
        home_name = home.get("name")
        away_name = away.get("name")

        if not fid or not date or not home_name or not away_name:
            continue

        fixtures.append(
            FixtureResponse(
                fixture_id=str(fid),
                date=date,
                home_team=home_name,
                away_team=away_name,
                home_logo=home.get("logo"),
                away_logo=away.get("logo"),
                league_name=league.get("name"),
            )
        )

    return fixtures
