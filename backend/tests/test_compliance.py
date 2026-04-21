"""
Integration tests for sprint 3.7 compliance/LGPD features.

Covers:
  - Registration requires accepted_terms=True and age_acknowledged=True
  - /users/me/export returns a portability JSON
  - /users/me/self-exclude deactivates the account
  - DELETE /users/me requires matching email + password, then anonymizes
  - /users/me/limits sets/clears caps
  - /wallet/payment-mode returns expected labels
"""
from __future__ import annotations

import os
import time

import httpx
import pytest


URL = os.environ.get("PATINHO_URL", "http://187.127.25.239")
PASSWORD = "TestPass123!"


def _health_ok() -> bool:
    try:
        return httpx.get(f"{URL}/api/health", timeout=5).status_code == 200
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _health_ok(),
    reason=f"Patinho API at {URL} not reachable",
)


def _register(client, username, email, phone, *, accepted=True, age_ack=True):
    return client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "email": email,
            "password": PASSWORD,
            "phone": phone,
            "birth_date": "1990-01-01",
            "accepted_terms": accepted,
            "age_acknowledged": age_ack,
        },
    )


@pytest.fixture(scope="module")
def client():
    with httpx.Client(base_url=URL, timeout=20.0) as c:
        yield c


def test_register_requires_accepted_terms(client):
    ts = int(time.time() * 1000)
    r = _register(client, f"cx_{ts}", f"cx_{ts}@example.com", f"+55119{ts % 100000000:08d}", accepted=False)
    assert r.status_code == 422
    assert "Termos" in r.text


def test_register_requires_age_acknowledged(client):
    ts = int(time.time() * 1000)
    r = _register(client, f"cy_{ts}", f"cy_{ts}@example.com", f"+55118{ts % 100000000:08d}", age_ack=False)
    assert r.status_code == 422
    assert "18 anos" in r.text


def test_register_success_writes_timestamps(client):
    ts = int(time.time() * 1000)
    r = _register(client, f"cz_{ts}", f"cz_{ts}@example.com", f"+55117{ts % 100000000:08d}")
    assert r.status_code in (200, 201)
    token = r.json()["access_token"]
    me = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    # response omits those fields by default — just confirm export carries them
    ex = client.get("/api/v1/users/me/export", headers={"Authorization": f"Bearer {token}"})
    assert ex.status_code == 200
    payload = ex.json()
    assert payload["user"]["accepted_terms_at"] is not None
    assert payload["user"]["age_acknowledged_at"] is not None


def test_data_export_shape(client):
    ts = int(time.time() * 1000)
    r = _register(client, f"ea_{ts}", f"ea_{ts}@example.com", f"+55116{ts % 100000000:08d}")
    token = r.json()["access_token"]
    ex = client.get("/api/v1/users/me/export", headers={"Authorization": f"Bearer {token}"})
    assert ex.status_code == 200
    data = ex.json()
    assert "user" in data and "wallet" in data and "transactions" in data and "participations" in data
    assert data["user"]["email"] == f"ea_{ts}@example.com"
    assert "exported_at" in data


def test_limits_update_and_clear(client):
    ts = int(time.time() * 1000)
    r = _register(client, f"la_{ts}", f"la_{ts}@example.com", f"+55115{ts % 100000000:08d}")
    token = r.json()["access_token"]

    # set
    r1 = client.patch(
        "/api/v1/users/me/limits",
        json={"monthly_deposit_cap": 500, "monthly_participation_cap": 200},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r1.status_code == 200
    body1 = r1.json()
    # Pydantic serializes Decimal as number (not string)
    assert float(body1["monthly_deposit_cap"]) == 500
    assert float(body1["monthly_participation_cap"]) == 200

    # clear with 0
    r2 = client.patch(
        "/api/v1/users/me/limits",
        json={"monthly_deposit_cap": 0},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.status_code == 200
    body2 = r2.json()
    assert body2["monthly_deposit_cap"] is None
    # other cap untouched
    assert float(body2["monthly_participation_cap"]) == 200


def test_self_exclude_deactivates(client):
    ts = int(time.time() * 1000)
    r = _register(client, f"sx_{ts}", f"sx_{ts}@example.com", f"+55114{ts % 100000000:08d}")
    token = r.json()["access_token"]

    r1 = client.post(
        "/api/v1/users/me/self-exclude",
        json={"confirm": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r1.status_code == 204

    r2 = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    # deactivated account should be rejected by get_current_active_user
    assert r2.status_code in (401, 403)


def test_delete_account_requires_matching_email(client):
    ts = int(time.time() * 1000)
    r = _register(client, f"da_{ts}", f"da_{ts}@example.com", f"+55113{ts % 100000000:08d}")
    token = r.json()["access_token"]
    r1 = client.request(
        "DELETE",
        "/api/v1/users/me",
        json={"confirm_email": "wrong@example.com", "password": PASSWORD},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r1.status_code == 400


def test_delete_account_requires_matching_password(client):
    ts = int(time.time() * 1000)
    email = f"db_{ts}@example.com"
    r = _register(client, f"db_{ts}", email, f"+55112{ts % 100000000:08d}")
    token = r.json()["access_token"]
    r1 = client.request(
        "DELETE",
        "/api/v1/users/me",
        json={"confirm_email": email, "password": "WrongPass999!"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r1.status_code == 401


def test_delete_account_anonymizes(client):
    ts = int(time.time() * 1000)
    email = f"dc_{ts}@example.com"
    r = _register(client, f"dc_{ts}", email, f"+55111{ts % 100000000:08d}")
    token = r.json()["access_token"]
    r1 = client.request(
        "DELETE",
        "/api/v1/users/me",
        json={"confirm_email": email, "password": PASSWORD},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r1.status_code == 204

    # Cannot log in with original credentials
    r2 = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": PASSWORD},
    )
    assert r2.status_code == 401


def test_payment_mode_endpoint(client):
    ts = int(time.time() * 1000)
    r = _register(client, f"pm_{ts}", f"pm_{ts}@example.com", f"+55110{ts % 100000000:08d}")
    token = r.json()["access_token"]
    r1 = client.get(
        "/api/v1/wallet/payment-mode",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r1.status_code == 200
    assert r1.json()["mode"] in {"test", "live", "unconfigured"}
