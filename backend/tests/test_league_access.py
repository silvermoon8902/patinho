"""
Integration-style tests for the league-access gates introduced in sprint 3.6c/d.

Run against any deployed Patinho instance:
    PATINHO_URL=http://localhost pytest tests/test_league_access.py
    PATINHO_URL=http://187.127.25.239 pytest tests/test_league_access.py

Skipped automatically if the target is unreachable — so CI doesn't fail when
nothing is running. When enabled, these lock the critical privacy gates:

  - Non-member cannot GET /bets/{id} of a league-scoped bet
  - Non-member cannot POST /bets/{id}/join of a league-scoped bet
  - Non-member cannot POST /bets/{id}/direct-join
  - Non-authenticated cannot GET /bets/invite/{token} of a league-scoped bet
  - email-invite on a league-scoped bet blocks non-league-member addresses
  - Non-member cannot GET /chat/{id}/messages of a league-scoped bet
  - Public (non-league) bet previews remain unauthenticated-accessible
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone

import httpx
import pytest


URL = os.environ.get("PATINHO_URL", "http://187.127.25.239")
PASSWORD = "TestPass123!"


def _health_ok() -> bool:
    try:
        r = httpx.get(f"{URL}/api/health", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _health_ok(),
    reason=f"Patinho API at {URL} is not reachable — skipping integration tests",
)


def _register(client: httpx.Client, username: str, email: str, phone: str) -> str:
    r = client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "email": email,
            "password": PASSWORD,
            "phone": phone,
            "birth_date": "1990-01-01",
        },
    )
    r.raise_for_status()
    return r.json()["access_token"]


def _make_league(client: httpx.Client, tok: str, name: str) -> str:
    r = client.post(
        "/api/v1/leagues",
        json={"name": name, "description": "test"},
        headers={"Authorization": f"Bearer {tok}"},
    )
    r.raise_for_status()
    return r.json()["id"]


def _make_bet(
    client: httpx.Client,
    tok: str,
    title: str,
    league_id: str | None = None,
) -> dict:
    closes_at = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
    body = {
        "title": title,
        "category": "custom",
        "options": ["A", "B"],
        "resolution_type": "voting",
        "entry_amount": 5,
        "max_participants": 10,
        "closes_at": closes_at,
    }
    if league_id:
        body["league_id"] = league_id
    r = client.post(
        "/api/v1/bets",
        json=body,
        headers={"Authorization": f"Bearer {tok}"},
    )
    r.raise_for_status()
    return r.json()


@pytest.fixture(scope="module")
def client() -> httpx.Client:
    with httpx.Client(base_url=URL, timeout=20.0) as c:
        yield c


@pytest.fixture(scope="module")
def tokens(client: httpx.Client) -> dict:
    ts = int(time.time() * 1000)
    a_email = f"a_{ts}@example.com"
    b_email = f"b_{ts}@example.com"
    a_tok = _register(client, f"at_a_{ts}", a_email, f"+5511{ts % 100000000:08d}")
    b_tok = _register(client, f"at_b_{ts}", b_email, f"+5512{ts % 100000000:08d}")
    return {
        "a": a_tok,
        "b": b_tok,
        "a_email": a_email,
        "b_email": b_email,
        "ts": ts,
    }


@pytest.fixture(scope="module")
def league_bet(client: httpx.Client, tokens: dict) -> dict:
    """Set up: A creates a league, creates a league-scoped bet. B is NOT in the league."""
    league_id = _make_league(client, tokens["a"], f"League {tokens['ts']}")
    bet = _make_bet(client, tokens["a"], "Private Test", league_id=league_id)
    return {"league_id": league_id, **bet}


@pytest.fixture(scope="module")
def public_bet(client: httpx.Client, tokens: dict) -> dict:
    return _make_bet(client, tokens["a"], "Public Test")


def test_non_member_cannot_get_league_bet(client, tokens, league_bet):
    r = client.get(
        f"/api/v1/bets/{league_bet['id']}",
        headers={"Authorization": f"Bearer {tokens['b']}"},
    )
    assert r.status_code == 404


def test_creator_can_get_league_bet(client, tokens, league_bet):
    r = client.get(
        f"/api/v1/bets/{league_bet['id']}",
        headers={"Authorization": f"Bearer {tokens['a']}"},
    )
    assert r.status_code == 200


def test_non_member_cannot_join_league_bet(client, tokens, league_bet):
    option_id = league_bet["options"][0]["id"]
    r = client.post(
        f"/api/v1/bets/{league_bet['id']}/join",
        json={"bet_option_id": option_id},
        headers={"Authorization": f"Bearer {tokens['b']}"},
    )
    assert r.status_code == 404


def test_non_member_cannot_direct_join_league_bet(client, tokens, league_bet):
    option_id = league_bet["options"][0]["id"]
    r = client.post(
        f"/api/v1/bets/{league_bet['id']}/direct-join",
        json={"bet_option_id": option_id, "amount": 5},
        headers={"Authorization": f"Bearer {tokens['b']}"},
    )
    assert r.status_code == 404


def test_unauthenticated_invite_token_blocked_on_league_bet(client, league_bet):
    r = client.get(f"/api/v1/bets/invite/{league_bet['invite_token']}")
    assert r.status_code == 404


def test_non_member_invite_token_blocked_on_league_bet(client, tokens, league_bet):
    r = client.get(
        f"/api/v1/bets/invite/{league_bet['invite_token']}",
        headers={"Authorization": f"Bearer {tokens['b']}"},
    )
    assert r.status_code == 404


def test_creator_can_access_invite_token_of_league_bet(client, tokens, league_bet):
    r = client.get(
        f"/api/v1/bets/invite/{league_bet['invite_token']}",
        headers={"Authorization": f"Bearer {tokens['a']}"},
    )
    assert r.status_code == 200


def test_unauthenticated_can_preview_public_bet(client, public_bet):
    """Regression guard: public bet preview must stay open for the invite page."""
    r = client.get(f"/api/v1/bets/invite/{public_bet['invite_token']}")
    assert r.status_code == 200


def test_non_member_cannot_list_chat_messages_of_league_bet(client, tokens, league_bet):
    r = client.get(
        f"/api/v1/chat/{league_bet['id']}/messages",
        headers={"Authorization": f"Bearer {tokens['b']}"},
    )
    assert r.status_code == 404


def test_email_invite_to_non_league_member_is_flagged(client, tokens, league_bet):
    r = client.post(
        f"/api/v1/bets/{league_bet['id']}/email-invite",
        json={"emails": ["outside@example.com", tokens["b_email"]]},
        headers={"Authorization": f"Bearer {tokens['a']}"},
    )
    assert r.status_code == 200
    results = r.json()["results"]
    # Both addresses are NOT in the league → both should be flagged
    assert results["outside@example.com"] == "not_in_league"
    assert results[tokens["b_email"]] == "not_in_league"


def test_list_bets_filter_by_league_requires_membership(client, tokens, league_bet):
    r = client.get(
        f"/api/v1/bets?league_id={league_bet['league_id']}",
        headers={"Authorization": f"Bearer {tokens['b']}"},
    )
    assert r.status_code == 403
