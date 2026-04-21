from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class LeagueResponse(BaseModel):
    id: str
    name: str
    api_id: int


class FixtureResponse(BaseModel):
    fixture_id: str
    date: datetime
    home_team: str
    away_team: str
    home_logo: str | None = None
    away_logo: str | None = None
    league_name: str | None = None


# League metadata used for display labels. Keys must match the keys of
# SUPPORTED_LEAGUES in app.integrations.api_football.
LEAGUE_LABELS: dict[str, str] = {
    "brasileirao": "Brasileirão Série A",
    "libertadores": "Copa Libertadores",
    "champions_league": "Champions League",
    "premier_league": "Premier League",
    "copa_do_brasil": "Copa do Brasil",
    "copa_sulamericana": "Copa Sul-Americana",
    "copa_do_mundo": "Copa do Mundo",
}


# Bet templates available for sport bets. Today we only expose
# "match_winner" but the dict is shaped to accept more templates later
# (exact_score, total_goals, both_teams_to_score, etc.).
BET_TEMPLATES: dict[str, dict[str, str]] = {
    "match_winner": {
        "label": "Quem vence?",
        "description": "Escolha o vencedor da partida",
    },
}


class SportBetCreate(BaseModel):
    fixture_id: str = Field(min_length=1, max_length=50)
    template: str = Field(default="match_winner")
    entry_amount: Decimal = Field(default=Decimal("5"), ge=5, le=1000)
    max_participants: int = Field(default=100, ge=2, le=100)
