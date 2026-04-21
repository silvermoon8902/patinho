import json
import logging
from datetime import datetime, timezone

import httpx
from redis.asyncio import Redis

from app.config import settings

logger = logging.getLogger(__name__)

API_F1_BASE_URL = "https://v1.formula-1.api-sports.io"

CACHE_TTL_SECONDS = 180  # 3 minutes


class APIFormula1Client:
    def __init__(self) -> None:
        self.api_key = settings.API_FOOTBALL_KEY
        self.base_url = API_F1_BASE_URL
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

        cached = await redis.get(cache_key)
        if cached:
            return json.loads(cached)

        if not self.api_key:
            logger.warning("API-Formula-1 key not configured")
            return None

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(url, headers=self._headers, params=params)

            if response.status_code != 200:
                logger.error(
                    "API-Formula-1 request failed: %s %s",
                    response.status_code,
                    response.text[:200],
                )
                return None

            data = response.json()
            await redis.set(cache_key, json.dumps(data), ex=CACHE_TTL_SECONDS)
            return data
        except httpx.TimeoutException:
            logger.error("API-Formula-1 request timed out: %s", url)
            return None
        except Exception:
            logger.exception("API-Formula-1 request error")
            return None

    async def list_upcoming_races(self, season: int) -> list[dict]:
        """
        List upcoming races for the given season.
        Filters out races already completed or with past dates.
        Returns up to 10 nearest races sorted by date ascending.

        Response items: {race_id, date, circuit_name, circuit_location, competition_name, season}
        """
        cache_key = f"apif1:races:{season}"
        data = await self._cached_get(
            cache_key,
            f"{self.base_url}/races",
            {"season": str(season)},
        )
        if not data:
            return []

        races = data.get("response", []) or []
        now = datetime.now(timezone.utc)

        mapped: list[dict] = []
        for r in races:
            status = (r.get("status") or "").lower()
            if status == "completed":
                continue

            race_date_raw = r.get("date")
            if not race_date_raw:
                continue

            try:
                race_date = datetime.fromisoformat(
                    race_date_raw.replace("Z", "+00:00")
                )
                if race_date.tzinfo is None:
                    race_date = race_date.replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                continue

            if race_date <= now:
                continue

            race_id = r.get("id")
            if race_id is None:
                continue

            circuit = r.get("circuit") or {}
            competition = r.get("competition") or {}
            location = competition.get("location") or {}

            mapped.append({
                "race_id": str(race_id),
                "date": race_date.isoformat(),
                "circuit_name": circuit.get("name") or "",
                "circuit_location": (
                    location.get("city")
                    or location.get("country")
                    or ""
                ),
                "competition_name": competition.get("name") or "",
                "season": r.get("season") or season,
            })

        mapped.sort(key=lambda x: x["date"])
        return mapped[:10]

    async def get_race(self, race_id: str) -> dict | None:
        """Fetch a single race by id."""
        cache_key = f"apif1:race:{race_id}"
        data = await self._cached_get(
            cache_key,
            f"{self.base_url}/races",
            {"id": str(race_id)},
        )
        if not data:
            return None

        response = data.get("response") or []
        if not response:
            return None
        return response[0]

    async def get_race_winner(self, race_id: str) -> str | None:
        """
        Return the winning driver's name for a finished race.
        Returns None if the race hasn't been completed yet.
        """
        cache_key = f"apif1:ranking:{race_id}"
        data = await self._cached_get(
            cache_key,
            f"{self.base_url}/rankings/races",
            {"race": str(race_id)},
        )
        if not data:
            return None

        rankings = data.get("response") or []
        if not rankings:
            return None

        # Ensure race is finished: the rankings endpoint returns standings
        # when the race completes; if no entry is in position 1 with a
        # finished status (time/points), treat as not yet resolved.
        for entry in rankings:
            position = entry.get("position")
            if position == 1:
                # Guard: if time or points is missing we consider it unresolved
                time_val = entry.get("time")
                points_val = entry.get("points")
                if time_val is None and points_val is None:
                    return None

                driver = entry.get("driver") or {}
                name = driver.get("name")
                if name:
                    return str(name)
                return None

        return None

    async def list_race_drivers(self, race_id: str) -> list[dict]:
        """
        Return drivers expected to compete in a race.

        Strategy:
          1. Try /rankings/races?race={race_id} — works once the grid is set
             or after the race is run.
          2. Fallback to /rankings/drivers?season={season} using the race's
             season — returns the current-season driver standings.

        Each item: {driver_id, name, team_name}
        """
        # Try rankings for this race first
        cache_key = f"apif1:ranking_drivers:{race_id}"
        data = await self._cached_get(
            cache_key,
            f"{self.base_url}/rankings/races",
            {"race": str(race_id)},
        )

        drivers: list[dict] = []
        if data:
            for entry in data.get("response") or []:
                driver = entry.get("driver") or {}
                team = entry.get("team") or {}
                driver_id = driver.get("id")
                name = driver.get("name")
                if driver_id is None or not name:
                    continue
                drivers.append({
                    "driver_id": str(driver_id),
                    "name": str(name),
                    "team_name": str(team.get("name") or ""),
                })

        if drivers:
            return drivers

        # Fallback: current-season driver standings
        race = await self.get_race(race_id)
        if not race:
            return []
        season = race.get("season")
        if not season:
            return []

        fallback_key = f"apif1:drivers:{season}"
        fallback_data = await self._cached_get(
            fallback_key,
            f"{self.base_url}/rankings/drivers",
            {"season": str(season)},
        )
        if not fallback_data:
            return []

        for entry in fallback_data.get("response") or []:
            driver = entry.get("driver") or {}
            team = entry.get("team") or {}
            driver_id = driver.get("id")
            name = driver.get("name")
            if driver_id is None or not name:
                continue
            drivers.append({
                "driver_id": str(driver_id),
                "name": str(name),
                "team_name": str(team.get("name") or ""),
            })

        return drivers

    async def close(self) -> None:
        if self._redis:
            await self._redis.close()
            self._redis = None


# Module-level singleton
api_f1_client = APIFormula1Client()
