import logging
from datetime import datetime

from fastapi import APIRouter, Query

from app.integrations.api_f1 import api_f1_client
from app.integrations.api_football import (
    SUPPORTED_LEAGUES,
    api_football_client,
)
from app.schemas.sports import (
    LEAGUE_LABELS,
    DriverOption,
    FixtureResponse,
    LeagueResponse,
    RaceResponse,
)

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


@router.get("/f1/races", response_model=list[RaceResponse])
async def list_f1_races(
    season: int = Query(default=2026, ge=2020, le=2099),
) -> list[RaceResponse]:
    """
    List upcoming F1 races for the given season.
    Returns [] when the upstream API fails or no races are found.
    """
    try:
        raw_races = await api_f1_client.list_upcoming_races(season)
    except Exception:
        logger.exception("Failed to list upcoming F1 races for season %s", season)
        return []

    races: list[RaceResponse] = []
    for raw in raw_races:
        race_id = raw.get("race_id")
        raw_date = raw.get("date")
        if not race_id or not raw_date:
            continue
        try:
            date_val = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
        except (ValueError, AttributeError, TypeError):
            continue
        races.append(
            RaceResponse(
                race_id=str(race_id),
                date=date_val,
                circuit_name=raw.get("circuit_name") or "",
                circuit_location=raw.get("circuit_location") or "",
                competition_name=raw.get("competition_name") or "",
            )
        )

    return races


@router.get(
    "/f1/races/{race_id}/drivers",
    response_model=list[DriverOption],
)
async def list_f1_race_drivers(race_id: str) -> list[DriverOption]:
    """
    List drivers available for the given race. Falls back to the
    current-season driver standings when no grid/results are set yet.
    """
    try:
        raw_drivers = await api_f1_client.list_race_drivers(race_id)
    except Exception:
        logger.exception("Failed to list F1 drivers for race %s", race_id)
        return []

    drivers: list[DriverOption] = []
    seen: set[str] = set()
    for raw in raw_drivers:
        did = raw.get("driver_id")
        name = raw.get("name")
        if not did or not name:
            continue
        if did in seen:
            continue
        seen.add(did)
        drivers.append(
            DriverOption(
                driver_id=str(did),
                name=str(name),
                team_name=str(raw.get("team_name") or ""),
            )
        )

    return drivers
