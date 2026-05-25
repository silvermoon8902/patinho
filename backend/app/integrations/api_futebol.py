"""
api-futebol.com.br integration.

Replaces api-football (api-sports.io) for football data. Same response
shape as api_football_client so the rest of the codebase (sports.py,
resolution_service.py, bet creation) can be swapped over with minimal
changes — the returned dicts mimic the api-football structure:

  {
    "fixture": {"id": ..., "date": "...", "status": {"short": "NS"|"FT"}},
    "teams":   {"home": {"name": ..., "logo": ...},
                "away": {"name": ..., "logo": ...}},
    "league":  {"name": ...},
    "goals":   {"home": ..., "away": ...},
  }

api-futebol uses Portuguese field names (partida_id, time_mandante,
placar_mandante, status="finalizado"|"agendada", data_realizacao_iso).
Those are translated here so callers stay provider-agnostic.
"""
from __future__ import annotations

import json
import logging

import httpx
from redis.asyncio import Redis

from app.config import settings

logger = logging.getLogger(__name__)

API_FUTEBOL_BASE_URL = "https://api.api-futebol.com.br/v1"
CACHE_TTL_SECONDS = 180


# api-futebol status → api-football short-status mapping. Anything not in
# this dict is treated as "not yet finished".
_STATUS_MAP = {
    "agendada": "NS",
    "ao-vivo": "LIVE",
    "em-andamento": "LIVE",
    "finalizado": "FT",
    "encerrada": "FT",
    "adiada": "PST",
    "cancelada": "CANC",
}

_FINISHED = {"FT", "AET", "PEN"}


class APIFutebolClient:
    def __init__(self) -> None:
        self.api_key = settings.API_FUTEBOL_KEY
        self.base_url = API_FUTEBOL_BASE_URL
        self._redis: Redis | None = None

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }

    async def _get_redis(self) -> Redis:
        if self._redis is None:
            self._redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
        return self._redis

    async def _cached_get(self, cache_key: str, path: str) -> dict | list | None:
        """GET with Redis cache. Returns parsed JSON or None on failure."""
        redis = await self._get_redis()
        cached = await redis.get(cache_key)
        if cached:
            return json.loads(cached)

        if not self.api_key:
            logger.warning("api-futebol key not configured")
            return None

        url = f"{self.base_url}{path}"
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url, headers=self._headers)
            if resp.status_code != 200:
                logger.error(
                    "api-futebol %s -> HTTP %s body=%s",
                    path, resp.status_code, resp.text[:200],
                )
                return None
            data = resp.json()
            await redis.set(cache_key, json.dumps(data), ex=CACHE_TTL_SECONDS)
            return data
        except httpx.TimeoutException:
            logger.error("api-futebol timeout: %s", path)
            return None
        except Exception:
            logger.exception("api-futebol request error: %s", path)
            return None

    # -------------- response shaping ---------------------------------

    @staticmethod
    def _partida_to_api_football(raw: dict) -> dict:
        """Translate an api-futebol partida dict to the api-football shape."""
        home = raw.get("time_mandante") or {}
        away = raw.get("time_visitante") or {}
        status_pt = (raw.get("status") or "").lower()
        short = _STATUS_MAP.get(status_pt, "NS")
        return {
            "fixture": {
                "id": raw.get("partida_id"),
                "date": raw.get("data_realizacao_iso"),
                "status": {"short": short, "long": status_pt},
            },
            "teams": {
                "home": {
                    "name": home.get("nome_popular"),
                    "logo": home.get("escudo"),
                },
                "away": {
                    "name": away.get("nome_popular"),
                    "logo": away.get("escudo"),
                },
            },
            "league": {
                "name": (raw.get("campeonato") or {}).get("nome_popular"),
            },
            "goals": {
                "home": raw.get("placar_mandante"),
                "away": raw.get("placar_visitante"),
            },
        }

    # -------------- public API ---------------------------------------

    async def list_championships(self) -> list[dict]:
        """Return the championships the API key has access to (paid plan scope)."""
        data = await self._cached_get("apifutebol:champs", "/campeonatos")
        if not isinstance(data, list):
            return []
        return data

    async def list_upcoming_fixtures(
        self, championship_id: int, _season: int | None = None
    ) -> tuple[list[dict], str]:
        """
        Return (upcoming_fixtures, status_tag) — matches api_football.

        The /campeonatos/{id}/partidas response is nested as
        {"partidas": {"partidas": {"<phase-slug>": {"<chave>": {"ida": ...,
        "volta": ...}}}}}. We flatten that into a list of partida dicts
        and filter to those not yet finished.

        status_tag values mirror api_football so the sports endpoint
        keeps its existing X-Sports-Reason behaviour: "ok",
        "no_matches_scheduled", "all_finished", "empty", "upstream_error".
        """
        cache_key = f"apifutebol:upcoming:{championship_id}"
        data = await self._cached_get(
            cache_key, f"/campeonatos/{championship_id}/partidas"
        )
        if data is None:
            return [], "upstream_error"

        # The endpoint sometimes returns {"message": "...", "code": 4xx}
        if isinstance(data, dict) and data.get("code") and data.get("message"):
            logger.warning(
                "api-futebol upstream error for champ %s: %s",
                championship_id, data.get("message"),
            )
            return [], "upstream_error"

        partidas = self._flatten_partidas(data)
        if not partidas:
            return [], "empty"

        upcoming: list[dict] = []
        finished = 0
        for raw in partidas:
            status = (raw.get("status") or "").lower()
            if status == "finalizado":
                finished += 1
                continue
            upcoming.append(self._partida_to_api_football(raw))
        upcoming.sort(key=lambda f: f["fixture"].get("date") or "")
        if not upcoming:
            return [], "all_finished" if finished else "empty"
        return upcoming, "ok"

    @staticmethod
    def _flatten_partidas(data: dict) -> list[dict]:
        """Walk the nested partidas tree and yield every leaf partida dict."""
        out: list[dict] = []

        def visit(node):
            if isinstance(node, dict):
                if "partida_id" in node:
                    out.append(node)
                else:
                    for v in node.values():
                        visit(v)
            elif isinstance(node, list):
                for v in node:
                    visit(v)

        visit(data)
        return out

    async def get_fixtures(self, fixture_ids: list[str | int]) -> list[dict]:
        """Fetch fixtures by ID. Cached per-fixture; mirrors api_football."""
        results: list[dict] = []
        for fid in fixture_ids:
            cache_key = f"apifutebol:partida:{fid}"
            data = await self._cached_get(cache_key, f"/partidas/{fid}")
            if isinstance(data, dict) and "partida_id" in data:
                results.append(self._partida_to_api_football(data))
        return results

    async def get_fixture_result(self, fixture_id: str | int) -> dict | None:
        """
        Get the result of a single fixture. Returns dict or None when the
        match isn't finished yet. Shape matches api_football so the
        resolution service code is provider-agnostic.

        Draws yield winner="Empate", winner_side="Draw".
        """
        cache_key = f"apifutebol:partida:{fixture_id}"
        data = await self._cached_get(cache_key, f"/partidas/{fixture_id}")
        if not isinstance(data, dict) or "partida_id" not in data:
            return None

        status_pt = (data.get("status") or "").lower()
        if status_pt != "finalizado":
            return None

        home_team = (data.get("time_mandante") or {}).get("nome_popular") or "Mandante"
        away_team = (data.get("time_visitante") or {}).get("nome_popular") or "Visitante"
        home_score = int(data.get("placar_mandante") or 0)
        away_score = int(data.get("placar_visitante") or 0)

        if home_score > away_score:
            winner, winner_side = home_team, "Home"
        elif away_score > home_score:
            winner, winner_side = away_team, "Away"
        else:
            winner, winner_side = "Empate", "Draw"

        return {
            "home_score": home_score,
            "away_score": away_score,
            "status": "FT",
            "winner": winner,
            "winner_side": winner_side,
            "home_team": home_team,
            "away_team": away_team,
        }

    async def close(self) -> None:
        if self._redis:
            await self._redis.close()
            self._redis = None


api_futebol_client = APIFutebolClient()
