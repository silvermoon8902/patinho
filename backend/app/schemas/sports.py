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


class RaceResponse(BaseModel):
    race_id: str
    date: datetime
    circuit_name: str
    circuit_location: str
    competition_name: str


class DriverOption(BaseModel):
    driver_id: str
    name: str
    team_name: str


class TennisMatchResponse(BaseModel):
    match_id: str
    date: datetime
    tour: str
    player1_name: str
    player2_name: str


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


# Bet templates available for sport bets. Each template declares the
# sport it applies to so the frontend can filter per sport kind.
BET_TEMPLATES: dict[str, dict[str, str]] = {
    "match_winner": {
        "sport": "football",
        "label": "Quem vence?",
        "description": "Escolha o vencedor da partida ou empate",
    },
    "exact_score": {
        "sport": "football",
        "label": "Acertar o placar",
        "description": "Escolha o placar exato da partida",
    },
    "f1_winner": {
        "sport": "f1",
        "label": "Vencedor da corrida",
        "description": "Escolha o piloto que vai vencer a corrida",
    },
    "tennis_winner": {
        "sport": "tennis",
        "label": "Vencedor da partida",
        "description": "Escolha o vencedor da partida de tênis",
    },
}


class SportBetCreate(BaseModel):
    template: str = Field(default="match_winner")
    fixture_id: str | None = Field(default=None, max_length=50)
    race_id: str | None = Field(default=None, max_length=50)
    tennis_match_id: str | None = Field(default=None, max_length=50)
    entry_amount: Decimal = Field(default=Decimal("5"), ge=5, le=1000)
    max_participants: int = Field(default=100, ge=2, le=100)
    # For f1_winner: optional subset of driver names to use as bet options
    driver_names: list[str] | None = None
