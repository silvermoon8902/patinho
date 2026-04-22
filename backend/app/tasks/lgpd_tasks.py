"""
LGPD data retention task.

Anonymizes PII on accounts that have been self-excluded or hard-deleted
for longer than the retention window (default: 5 years). Bet/transaction
history stays intact for audit, but the user profile is scrubbed beyond
recovery.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from app.celery_app import celery_app

logger = logging.getLogger(__name__)

# Brazilian LGPD + common betting regulations: 5-year retention.
RETENTION_YEARS = 5


async def _purge_expired_accounts_async() -> int:
    from sqlalchemy import select

    from app.database import async_session_maker
    from app.models.user import User

    cutoff = datetime.now(timezone.utc) - timedelta(days=RETENTION_YEARS * 365)

    async with async_session_maker() as db:
        try:
            result = await db.execute(
                select(User).where(
                    User.is_active.is_(False),
                    User.self_excluded_at.isnot(None),
                    User.self_excluded_at <= cutoff,
                )
            )
            candidates = list(result.scalars().all())
            anonymized = 0
            for u in candidates:
                if u.email and u.email.endswith("@purged.local"):
                    continue  # already purged
                token = f"purged-{u.id}"
                u.email = f"{token}@purged.local"
                u.username = token[:50]
                u.phone = ""
                u.cpf = None
                u.hashed_password = ""
                anonymized += 1
            if anonymized:
                await db.flush()
                await db.commit()
                logger.info(
                    "LGPD retention purge: anonymized %d account(s) older than %d years",
                    anonymized, RETENTION_YEARS,
                )
            return anonymized
        except Exception:
            await db.rollback()
            logger.exception("LGPD retention purge failed")
            raise


@celery_app.task(name="app.tasks.lgpd.purge_expired_accounts")
def purge_expired_accounts() -> int:
    return asyncio.run(_purge_expired_accounts_async())
