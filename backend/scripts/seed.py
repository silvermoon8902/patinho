"""
Seed script for QA / demo environments.

Creates:
  - 5 test users (with wallets pre-funded)
  - 1 admin user
  - 3 private leagues
  - A mix of open / pending / resolved bets
  - Example tournament bet for the WC 2026 bolão

Idempotent: skips users/leagues that already exist by username/name.

Run inside the backend container:
  docker compose exec backend python -m app.scripts.seed
"""
from __future__ import annotations

import asyncio
import secrets
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_maker
from app.models.bet import Bet, BetStatus, ResolutionType
from app.models.bet_option import BetOption
from app.models.league import League
from app.models.league_membership import LeagueMembership
from app.models.user import User
from app.models.wallet import Wallet
from app.utils.security import hash_password

PASSWORD = "TestPass123!"
SEED_USERS = [
    ("alice_seed", "alice@seed.local", True),     # (username, email, is_admin)
    ("bob_seed",   "bob@seed.local",   False),
    ("carol_seed", "carol@seed.local", False),
    ("dave_seed",  "dave@seed.local",  False),
    ("eve_seed",   "eve@seed.local",   False),
    ("frank_seed", "frank@seed.local", False),
]


async def _upsert_user(db: AsyncSession, username: str, email: str, is_admin: bool, balance: Decimal) -> User:
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if user:
        print(f"  user {username} already exists")
        return user
    now = datetime.now(timezone.utc)
    user = User(
        email=email,
        username=username,
        hashed_password=hash_password(PASSWORD),
        phone="+5511900000000",
        birth_date=datetime(1990, 1, 1).date(),
        is_admin=is_admin,
        is_active=True,
        accepted_terms_at=now,
        terms_version="v1",
        age_acknowledged_at=now,
    )
    db.add(user)
    await db.flush()
    wallet = Wallet(user_id=user.id, balance=balance)
    db.add(wallet)
    await db.flush()
    print(f"  + user {username}  (admin={is_admin}, R$ {balance:.2f})")
    return user


async def _upsert_league(db: AsyncSession, name: str, owner: User, members: list[User]) -> League:
    result = await db.execute(select(League).where(League.name == name))
    league = result.scalar_one_or_none()
    if league:
        print(f"  league '{name}' already exists")
        return league
    league = League(
        name=name,
        description=f"Liga seed: {name}",
        owner_id=owner.id,
        invite_code=secrets.token_urlsafe(8)[:12],
    )
    db.add(league)
    await db.flush()
    for u in [owner, *members]:
        db.add(LeagueMembership(league_id=league.id, user_id=u.id))
    await db.flush()
    print(f"  + league '{name}' with {1 + len(members)} member(s)")
    return league


async def _create_bet(
    db: AsyncSession,
    creator: User,
    *,
    title: str,
    options: list[str],
    league_id=None,
    closes_in_hours: int = 48,
    entry: Decimal = Decimal("10"),
    status_override: BetStatus = BetStatus.OPEN,
) -> Bet:
    # idempotence by title
    result = await db.execute(select(Bet).where(Bet.title == title))
    if result.scalar_one_or_none():
        print(f"  bet '{title}' already exists")
        return
    bet = Bet(
        creator_id=creator.id,
        title=title,
        description="",
        invite_token=secrets.token_urlsafe(12)[:24],
        category="custom",
        resolution_type=ResolutionType.VOTING,
        status=status_override,
        entry_amount=entry,
        max_participants=20,
        closes_at=datetime.now(timezone.utc) + timedelta(hours=closes_in_hours),
        league_id=league_id,
    )
    db.add(bet)
    await db.flush()
    for lbl in options:
        db.add(BetOption(bet_id=bet.id, label=lbl))
    await db.flush()
    print(f"  + bet '{title}' (status={status_override.value}, entry=R$ {entry})")
    return bet


async def main():
    print("=== Patinho seed ===")
    async with async_session_maker() as db:
        try:
            users = []
            for (username, email, is_admin) in SEED_USERS:
                u = await _upsert_user(db, username, email, is_admin, Decimal("500.00"))
                users.append(u)
            alice, bob, carol, dave, eve, frank = users

            await _upsert_league(db, "Galera do Escritório", alice, [bob, carol])
            await _upsert_league(db, "Família Silva", bob, [carol, dave])
            await _upsert_league(db, "Vizinhos da Rua 1", dave, [eve, frank])

            await _create_bet(db, alice, title="Quem vence o próximo clássico?",
                              options=["Time Azul", "Empate", "Time Vermelho"])
            await _create_bet(db, bob, title="Vai chover no sábado?",
                              options=["Sim", "Não"], closes_in_hours=12, entry=Decimal("5"))
            await _create_bet(db, carol, title="Qual prato pro jantar do domingo?",
                              options=["Pizza", "Churrasco", "Feijoada"], entry=Decimal("20"))

            await db.commit()
            print("\n=== Seed complete ===")
            print(f"Default password for all seed users: {PASSWORD}")
        except Exception as e:
            await db.rollback()
            print(f"FATAL: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(main())
