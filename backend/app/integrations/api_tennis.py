import json
import logging
from datetime import datetime, timedelta, timezone

import httpx
from redis.asyncio import Redis

from app.config import settings

logger = logging.getLogger(__name__)

API_TENNIS_BASE_URL = "https://v1.tennis.api-sports.io"

CACHE_TTL_SECONDS = 180  # 3 minutes

# Subset of tour → league IDs used by api-sports. These values may need to be
# adjusted once the subscription is active and the real IDs are visible. They
# are used only as a best-effort filter; if the API call fails we fall back to
# a plain per-date fetch.
TOUR_LEAGUE_IDS: dict[str, int] = {
    "ATP": 1,
    "WTA": 2,
}


class APITennisClient:
    def __init__(self) -> None:
        self.api_key = settings.API_FOOTBALL_KEY
        self.base_url = API_TENNIS_BASE_URL
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
            logger.warning("API-Tennis key not configured")
            return None

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(url, headers=self._headers, params=params)

            if response.status_code != 200:
                # 401/403 typically means no active Tennis subscription — log
                # at info level and gracefully return None.
                if response.status_code in (401, 403):
                    logger.info(
                        "API-Tennis access denied (status=%s). Tennis subscription may be inactive.",
                        response.status_code,
                    )
                else:
                    logger.error(
                        "API-Tennis request failed: %s %s",
                        response.status_code,
                        response.text[:200],
                    )
                return None

            data = response.json()
            await redis.set(cache_key, json.dumps(data), ex=CACHE_TTL_SECONDS)
            return data
        except httpx.TimeoutException:
            logger.error("API-Tennis request timed out: %s", url)
            return None
        except Exception:
            logger.exception("API-Tennis request error")
            return None

    def _extract_player_names(self, raw: dict) -> tuple[str | None, str | None]:
        """Extract player names from a /games item.

        API-Tennis may expose players under different shapes; try several.
        """
        players = raw.get("players") or {}
        if isinstance(players, dict):
            first = players.get("first") or players.get("home") or {}
            second = players.get("second") or players.get("away") or {}
            n1 = (first.get("name") if isinstance(first, dict) else None) or None
            n2 = (second.get("name") if isinstance(second, dict) else None) or None
            if n1 or n2:
                return n1, n2

        # Alternative shape: teams-like
        teams = raw.get("teams") or {}
        if isinstance(teams, dict):
            home = teams.get("home") or {}
            away = teams.get("away") or {}
            n1 = (home.get("name") if isinstance(home, dict) else None) or None
            n2 = (away.get("name") if isinstance(away, dict) else None) or None
            if n1 or n2:
                return n1, n2

        return None, None

    def _extract_start_date(self, raw: dict) -> str | None:
        """Try to extract an ISO date/time string for the match start."""
        # Common shapes
        for key in ("date", "time", "datetime"):
            val = raw.get(key)
            if isinstance(val, str) and val:
                return val
        # Nested
        fixture = raw.get("fixture")
        if isinstance(fixture, dict):
            for key in ("date", "time", "datetime"):
                val = fixture.get(key)
                if isinstance(val, str) and val:
                    return val
        return None

    def _extract_tour(self, raw: dict) -> str:
        """Best-effort to determine ATP vs WTA from the raw item."""
        league = raw.get("league") or {}
        name = (league.get("name") or "").upper() if isinstance(league, dict) else ""
        if "WTA" in name:
            return "WTA"
        if "ATP" in name:
            return "ATP"
        # Fallback: check raw.tour or raw.type
        for key in ("tour", "type", "category"):
            val = raw.get(key)
            if isinstance(val, str):
                v = val.upper()
                if "WTA" in v:
                    return "WTA"
                if "ATP" in v:
                    return "ATP"
        return ""

    async def _fetch_games_for_date(self, date_str: str) -> list[dict]:
        cache_key = f"apitennis:games:date:{date_str}"
        data = await self._cached_get(
            cache_key,
            f"{self.base_url}/games",
            {"date": date_str, "timezone": "UTC"},
        )
        if not data:
            return []
        return data.get("response", []) or []

    async def list_upcoming_matches(
        self, tour: str = "", season: int | None = None
    ) -> list[dict]:
        """
        List upcoming tennis matches for the next 14 days.

        tour: "ATP", "WTA", or "" for both.
        season: unused in the date-based strategy but kept for API symmetry.

        Returns up to 30 nearest matches sorted by date ascending. Each item:
        {match_id, date, tour, player1_name, player2_name}
        """
        tour_norm = (tour or "").upper().strip()
        if tour_norm not in ("ATP", "WTA", ""):
            tour_norm = ""

        now = datetime.now(timezone.utc)
        mapped: list[dict] = []
        seen_ids: set[str] = set()

        # Fetch 14 days ahead (including today)
        for day_offset in range(0, 14):
            date_str = (now + timedelta(days=day_offset)).strftime("%Y-%m-%d")
            try:
                raw_games = await self._fetch_games_for_date(date_str)
            except Exception:
                logger.exception("Failed to fetch tennis games for %s", date_str)
                continue

            for raw in raw_games:
                match_id = raw.get("id")
                if match_id is None:
                    continue
                match_id_str = str(match_id)
                if match_id_str in seen_ids:
                    continue

                status_obj = raw.get("status") or {}
                status_val = ""
                if isinstance(status_obj, dict):
                    status_val = str(
                        status_obj.get("short")
                        or status_obj.get("long")
                        or ""
                    ).lower()
                elif isinstance(status_obj, str):
                    status_val = status_obj.lower()

                # Skip already-finished matches
                if status_val in ("ft", "finished", "completed", "canc", "cancelled"):
                    continue

                raw_date = self._extract_start_date(raw)
                if not raw_date:
                    continue

                try:
                    match_date = datetime.fromisoformat(
                        raw_date.replace("Z", "+00:00")
                    )
                    if match_date.tzinfo is None:
                        match_date = match_date.replace(tzinfo=timezone.utc)
                except (ValueError, TypeError):
                    continue

                if match_date <= now:
                    continue

                p1, p2 = self._extract_player_names(raw)
                if not p1 or not p2:
                    continue

                match_tour = self._extract_tour(raw)
                if tour_norm and match_tour and match_tour != tour_norm:
                    continue

                seen_ids.add(match_id_str)
                mapped.append({
                    "match_id": match_id_str,
                    "date": match_date.isoformat(),
                    "tour": match_tour or tour_norm or "",
                    "player1_name": p1,
                    "player2_name": p2,
                })

        mapped.sort(key=lambda x: x["date"])
        return mapped[:30]

    async def get_match(self, match_id: str) -> dict | None:
        """Fetch a single match by id."""
        cache_key = f"apitennis:match:{match_id}"
        data = await self._cached_get(
            cache_key,
            f"{self.base_url}/games",
            {"id": str(match_id)},
        )
        if not data:
            return None
        response = data.get("response") or []
        if not response:
            return None
        return response[0]

    async def get_match_winner(self, match_id: str) -> str | None:
        """
        Return the winning player's name for a finished match.
        Returns None if the match hasn't been completed yet.
        """
        match = await self.get_match(match_id)
        if not match:
            return None

        status_obj = match.get("status") or {}
        status_val = ""
        if isinstance(status_obj, dict):
            status_val = str(
                status_obj.get("short")
                or status_obj.get("long")
                or ""
            ).lower()
        elif isinstance(status_obj, str):
            status_val = status_obj.lower()

        if status_val not in ("ft", "finished", "completed"):
            return None

        # Try the common "winner" shapes
        scores = match.get("scores") or {}
        # Some APIs expose "winner" at top level as a boolean on each player
        players = match.get("players") or {}
        if isinstance(players, dict):
            first = players.get("first") or players.get("home") or {}
            second = players.get("second") or players.get("away") or {}
            if isinstance(first, dict) and first.get("winner") is True:
                name = first.get("name")
                if name:
                    return str(name)
            if isinstance(second, dict) and second.get("winner") is True:
                name = second.get("name")
                if name:
                    return str(name)

        # Try teams-like shape
        teams = match.get("teams") or {}
        if isinstance(teams, dict):
            home = teams.get("home") or {}
            away = teams.get("away") or {}
            if isinstance(home, dict) and home.get("winner") is True:
                name = home.get("name")
                if name:
                    return str(name)
            if isinstance(away, dict) and away.get("winner") is True:
                name = away.get("name")
                if name:
                    return str(name)

        # Fallback: compare set scores if provided
        if isinstance(scores, dict):
            p1_sets = 0
            p2_sets = 0
            for set_info in scores.values():
                if not isinstance(set_info, dict):
                    continue
                h = set_info.get("home")
                a = set_info.get("away")
                try:
                    hi = int(h) if h is not None else None
                    ai = int(a) if a is not None else None
                except (ValueError, TypeError):
                    continue
                if hi is None or ai is None:
                    continue
                if hi > ai:
                    p1_sets += 1
                elif ai > hi:
                    p2_sets += 1

            if p1_sets != p2_sets:
                p1, p2 = self._extract_player_names(match)
                if p1_sets > p2_sets and p1:
                    return p1
                if p2_sets > p1_sets and p2:
                    return p2

        return None

    async def close(self) -> None:
        if self._redis:
            await self._redis.close()
            self._redis = None


# Module-level singleton
api_tennis_client = APITennisClient()
