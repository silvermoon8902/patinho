"""Bet schema validation tests."""
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas.bet import BetCreate


def _base_payload(**overrides):
    base = {
        "title": "Vencedor do jogo",
        "description": "",
        "category": "custom",
        "resolution_type": "voting",
        "options": ["Time A", "Time B"],
        "closes_at": datetime(2099, 1, 1, tzinfo=timezone.utc),
        "entry_amount": 5,
        "max_participants": 10,
    }
    base.update(overrides)
    return base


def test_custom_bet_requires_regulamento():
    """Voting bets must carry a description (regulamento) of at least 20 chars."""
    with pytest.raises(ValidationError) as exc:
        BetCreate(**_base_payload(description=""))
    assert "regulamento" in str(exc.value).lower()


def test_custom_bet_rejects_too_short_regulamento():
    with pytest.raises(ValidationError):
        BetCreate(**_base_payload(description="Só isso."))


def test_custom_bet_accepts_full_regulamento():
    payload = _base_payload(
        description="Vence quem acertar o vencedor do jogo no tempo normal.",
    )
    bet = BetCreate(**payload)
    assert bet.resolution_type == "voting"
    assert bet.description.startswith("Vence quem")


def test_auto_api_bet_does_not_require_description():
    """Sport bets read rules from the fixture — description stays optional."""
    payload = _base_payload(
        resolution_type="auto_api",
        category="football",
        description=None,
    )
    bet = BetCreate(**payload)
    assert bet.description is None
