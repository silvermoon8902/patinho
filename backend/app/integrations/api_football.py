import json
import logging

import httpx
from redis.asyncio import Redis

from app.config import settings

logger = logging.getLogger(__name__)

API_FOOTBALL_BASE_URL = "https://v3.football.api-sports.io"

SUPPORTED_LEAGUES: dict[str, int] = {
    "brasileirao": 71,
    "libertadores": 13,
    "champions_league": 2,
    "premier_league": 39,
    "copa_do_brasil": 73,
    "copa_sulamericana": 14,
    "copa_do_mundo": 1,
}

CACHE_TTL_SECONDS = 180  # 3 minutes


class APIFootballClient:
    def __init__(self) -> None:
        self.api_key = settings.API_FOOTBALL_KEY
        self.base_url = API_FOOTBALL_BASE_URL
        self._redis: Redis | None = None

    async def _get_redis(self) -> Redis:
        if self._redis is None:
            self._redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
        return self._redis

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "x-apisports-key": self.api_key,
            "Content-Type": "application/json",
        }

    async def _cached_get(self, cache_key: str, url: str, params: dict) -> dict | None:
        """GET with Redis cache. Returns parsed JSON or None on failure."""
        redis = await self._get_redis()

        # Check cache
        cached = await redis.get(cache_key)
        if cached:
            return json.loads(cached)

        if not self.api_key:
            logger.warning("API-Football key not configured")
            return None

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(url, headers=self._headers, params=params)

            if response.status_code != 200:
                logger.error(
                    "API-Football request failed: %s %s",
                    response.status_code,
                    response.text[:200],
                )
                return None

            data = response.json()

            # Cache result
            await redis.set(cache_key, json.dumps(data), ex=CACHE_TTL_SECONDS)
            return data
        except httpx.TimeoutException:
            logger.error("API-Football request timed out: %s", url)
            return None
        except Exception:
            logger.exception("API-Football request error")
            return None

    async def get_fixtures(self, fixture_ids: list[str]) -> list[dict]:
        """
        Fetch fixtures by ID. Fetches one at a time (free plan doesn't support
        batch `ids=` parameter). Cached per fixture.
        """
        if not fixture_ids:
            return []

        results: list[dict] = []
        for fid in fixture_ids:
            cache_key = f"apifootball:fixture:{fid}"
            data = await self._cached_get(
                cache_key,
                f"{self.base_url}/fixtures",
                {"id": str(fid)},
            )
            if data:
                results.extend(data.get("response", []))

        return results

    async def search_fixtures(self, league_id: int, date: str) -> list[dict]:
        """
        Search upcoming fixtures for a league on a given date.
        date format: YYYY-MM-DD
        """
        cache_key = f"apifootball:search:{league_id}:{date}"

        data = await self._cached_get(
            cache_key,
            f"{self.base_url}/fixtures",
            {"league": str(league_id), "date": date, "season": "2026"},
        )

        if not data:
            return []

        return data.get("response", [])

    async def list_upcoming_fixtures(self, league_id: int, season: int) -> list[dict]:
        """
        List all fixtures for a league+season that are not yet finished.
        Free plan supports fetching by league+season (returns the full season).
        We filter for upcoming matches (status NS/TBD).
        """
        cache_key = f"apifootball:upcoming:{league_id}:{season}"
        data = await self._cached_get(
            cache_key,
            f"{self.base_url}/fixtures",
            {"league": str(league_id), "season": str(season)},
        )
        if not data:
            return []

        fixtures = data.get("response", [])
        errors = data.get("errors") or {}
        results_total = data.get("results")

        # Tally statuses for diagnostics — when the upstream returns
        # only finished matches we want to see that in the logs instead
        # of silently returning [].
        status_counts: dict[str, int] = {}
        for f in fixtures:
            s = (f.get("fixture", {}).get("status", {}) or {}).get("short") or "?"
            status_counts[s] = status_counts.get(s, 0) + 1

        upcoming_statuses = {"NS", "TBD", "PST"}
        upcoming = [
            f for f in fixtures
            if f.get("fixture", {}).get("status", {}).get("short") in upcoming_statuses
        ]
        upcoming.sort(key=lambda f: f.get("fixture", {}).get("date") or "")

        if not upcoming:
            logger.warning(
                "api-football empty result league=%s season=%s "
                "upstream_total=%s upstream_errors=%s status_counts=%s",
                league_id, season, results_total, errors, status_counts,
            )
        return upcoming

    async def get_fixture_result(self, fixture_id: str) -> dict | None:
        """
        Get the result of a single fixture.
        Returns {home_score, away_score, status, winner} or None if not finished.

        winner values: "Home", "Draw", "Away"
        """
        fixtures = await self.get_fixtures([fixture_id])
        if not fixtures:
            return None

        fixture = fixtures[0]
        fixture_data = fixture.get("fixture", {})
        status_data = fixture_data.get("status", {})
        short_status = status_data.get("short", "")

        # Match is not finished
        finished_statuses = {"FT", "AET", "PEN"}
        if short_status not in finished_statuses:
            return None

        goals = fixture.get("goals", {})
        home_score = goals.get("home", 0) or 0
        away_score = goals.get("away", 0) or 0

        teams = fixture.get("teams", {})
        home_team = teams.get("home", {}).get("name", "Home")
        away_team = teams.get("away", {}).get("name", "Away")

        if home_score > away_score:
            winner = home_team
            winner_side = "Home"
        elif away_score > home_score:
            winner = away_team
            winner_side = "Away"
        else:
            winner = "Empate"
            winner_side = "Draw"

        return {
            "home_score": home_score,
            "away_score": away_score,
            "status": short_status,
            "winner": winner,
            "winner_side": winner_side,
            "home_team": home_team,
            "away_team": away_team,
        }

    async def close(self) -> None:
        if self._redis:
            await self._redis.close()
            self._redis = None


# Module-level singleton
api_football_client = APIFootballClient()
