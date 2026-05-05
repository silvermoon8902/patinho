import asyncio
import logging
from datetime import datetime, timezone

from app.celery_app import celery_app

logger = logging.getLogger(__name__)


async def _notify_creator_voting_bet_locked(db, bet) -> None:
    """Best-effort: email the creator that they need to declare a winner.

    Failures (SMTP down, no email on file) are logged but never block the
    state transition — the UI banner is the primary signal.
    """
    try:
        from app.config import settings
        from app.models.user import User
        from app.services import email_service

        creator = await db.get(User, bet.creator_id)
        if not creator or not getattr(creator, "email", None):
            return
        bet_url = f"{(settings.APP_URL or '').rstrip('/') or 'http://187.127.25.239'}/bets/{bet.id}"
        html, text = email_service.render_bet_locked_creator(
            creator_name=creator.username or "criador",
            bet_title=bet.title,
            bet_url=bet_url,
        )
        await email_service.send_email(
            creator.email,
            f"Hora de declarar o vencedor — {bet.title}",
            html,
            text,
        )
    except Exception:
        logger.exception(
            "Failed to send locked-bet reminder to creator of bet %s", bet.id
        )


async def _lock_expired_bets_async() -> int:
    """
    Find open bets past closes_at.
    For auto_api: set status=locked.
    For voting: start voting phase.
    """
    from sqlalchemy import select

    from app.database import async_session_maker
    from app.models.bet import Bet, BetStatus, ResolutionType

    async with async_session_maker() as db:
        try:
            now = datetime.now(timezone.utc)

            result = await db.execute(
                select(Bet).where(
                    Bet.status == BetStatus.OPEN,
                    Bet.closes_at <= now,
                )
            )
            bets = list(result.scalars().all())

            if not bets:
                logger.debug("No expired open bets to lock")
                return 0

            logger.info("Locking %d expired open bets", len(bets))
            locked_count = 0
            voting_locked: list = []

            for bet in bets:
                try:
                    if bet.resolution_type == ResolutionType.AUTO_API:
                        bet.status = BetStatus.LOCKED
                        locked_count += 1
                        logger.info("Locked sports bet %s", bet.id)
                    elif bet.resolution_type == ResolutionType.VOTING:
                        bet.status = BetStatus.LOCKED
                        locked_count += 1
                        voting_locked.append(bet)
                        logger.info(
                            "Locked voting bet %s awaiting creator declaration",
                            bet.id,
                        )
                except Exception:
                    logger.exception("Error locking/transitioning bet %s", bet.id)
                    continue

            await db.commit()
            # Notifications go out AFTER the commit so a failed SMTP call
            # cannot rollback the state transition.
            for bet in voting_locked:
                await _notify_creator_voting_bet_locked(db, bet)
            logger.info("Processed %d/%d expired bets", locked_count, len(bets))
            return locked_count
        except Exception:
            await db.rollback()
            logger.exception("Error in lock_expired_bets task")
            raise


@celery_app.task(name="app.tasks.betting.lock_expired_bets")
def lock_expired_bets() -> int:
    """Celery beat task: lock expired open bets or start voting."""
    return asyncio.run(_lock_expired_bets_async())


# Voting bets that the creator never declares should not trap participant
# funds forever. After this many days in LOCKED with no declared winner
# we cancel the bet and refund every participant (creator included).
STALE_LOCK_REFUND_DAYS = 7


async def _refund_stale_locked_bets_async() -> int:
    """Auto-cancel + refund voting bets stuck in LOCKED for too long.

    Safety net for the case where the bet creator disappears, gets sick,
    or simply forgets to declare the winner — without this, participant
    funds stay frozen indefinitely. No admin fee is charged.
    """
    from datetime import timedelta

    from sqlalchemy import select

    from app.database import async_session_maker
    from app.models.bet import Bet, BetStatus, ResolutionType
    from app.services import dispute_service

    cutoff = datetime.now(timezone.utc) - timedelta(days=STALE_LOCK_REFUND_DAYS)
    refunded = 0
    async with async_session_maker() as db:
        try:
            rows = (
                await db.execute(
                    select(Bet).where(
                        Bet.status == BetStatus.LOCKED,
                        Bet.resolution_type == ResolutionType.VOTING,
                        Bet.declared_winner_option_id.is_(None),
                        Bet.closes_at <= cutoff,
                    )
                )
            ).scalars().all()
            for bet in rows:
                try:
                    await dispute_service.refund_all(db, bet.id)
                    refunded += 1
                    logger.warning(
                        "Auto-cancelled stale locked bet %s "
                        "(creator never declared after %d days)",
                        bet.id, STALE_LOCK_REFUND_DAYS,
                    )
                except Exception:
                    logger.exception(
                        "Error auto-cancelling stale locked bet %s", bet.id
                    )
                    continue
            await db.commit()
        except Exception:
            await db.rollback()
            logger.exception("Error in refund_stale_locked_bets task")
            raise
    return refunded


@celery_app.task(name="app.tasks.betting.refund_stale_locked_bets")
def refund_stale_locked_bets() -> int:
    """Celery beat task: refund participants of stale locked voting bets."""
    return asyncio.run(_refund_stale_locked_bets_async())
