import logging
from datetime import datetime, timedelta, timezone
from decimal import ROUND_DOWN, Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin_fee import AdminFee, FeeType
from app.models.bet import Bet, BetStatus
from app.models.bet_option import BetOption
from app.models.participation import Participation
from app.models.platform_config import PlatformConfig
from app.services import wallet_service

logger = logging.getLogger(__name__)


async def _get_fee_config(db: AsyncSession) -> tuple[str, Decimal]:
    """Read fee configuration from platform_config table."""
    result = await db.execute(
        select(PlatformConfig).where(PlatformConfig.key == "default_fee")
    )
    config = result.scalar_one_or_none()

    if config and config.value:
        fee_type = config.value.get("fee_type", "percent")
        fee_value = Decimal(str(config.value.get("fee_value", "8")))
        return fee_type, fee_value

    # Default: 8% platform fee
    return "percent", Decimal("8")


async def distribute_prizes(
    db: AsyncSession, bet_id: UUID, winning_option_id: UUID
) -> None:
    """
    Distribute prizes for a resolved bet. Must run inside a single transaction.

    1. Read fee config
    2. Calculate prize pool and admin fee
    3. Distribute net pool proportionally among winners
    4. Unlock loser funds (no credit)
    5. Record admin fee and update bet status
    """
    # Load bet
    bet = await db.get(Bet, bet_id)
    if not bet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bet not found",
        )

    # Load all participations
    result = await db.execute(
        select(Participation).where(Participation.bet_id == bet_id)
    )
    participations = list(result.scalars().all())

    if not participations:
        logger.warning("No participations found for bet %s", bet_id)
        return

    # Validate winning option belongs to this bet
    winning_option = await db.get(BetOption, winning_option_id)
    if not winning_option or winning_option.bet_id != bet_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid winning option for this bet",
        )

    # Calculate prize pool
    prize_pool = sum(p.amount for p in participations)

    # Get fee config
    fee_type, fee_value = await _get_fee_config(db)

    # Calculate admin fee
    if fee_type == "percent":
        admin_fee_amount = (prize_pool * fee_value / Decimal("100")).quantize(
            Decimal("0.01"), rounding=ROUND_DOWN
        )
    else:  # fixed
        admin_fee_amount = min(fee_value, prize_pool)

    net_pool = prize_pool - admin_fee_amount

    # Split winners and losers
    winners = [p for p in participations if p.bet_option_id == winning_option_id]
    losers = [p for p in participations if p.bet_option_id != winning_option_id]

    if not winners:
        # No winners: refund everyone minus fee? Per spec, still distribute.
        # If nobody picked the winning option, net_pool goes unclaimed.
        # Unlock all as losers with no prize.
        for p in participations:
            await wallet_service.unlock_funds(db, p.user_id, p.amount, bet_id)
            p.prize_amount = Decimal("0")

        # Still record the fee even if no winners
        admin_fee = AdminFee(
            bet_id=bet_id,
            fee_type=FeeType(fee_type),
            fee_value=fee_value,
            amount=admin_fee_amount,
            prize_pool_snapshot=prize_pool,
        )
        db.add(admin_fee)
    else:
        total_winning_entries = sum(w.amount for w in winners)

        # Credit each winner proportionally
        for w in winners:
            prize = (net_pool * w.amount / total_winning_entries).quantize(
                Decimal("0.01"), rounding=ROUND_DOWN
            )
            await wallet_service.unlock_and_credit_prize(
                db, w.user_id, w.amount, prize, bet_id
            )
            w.prize_amount = prize

        # Unlock loser funds (no credit)
        for p in losers:
            await wallet_service.unlock_funds(db, p.user_id, p.amount, bet_id)
            p.prize_amount = Decimal("0")

        # Record admin fee
        admin_fee = AdminFee(
            bet_id=bet_id,
            fee_type=FeeType(fee_type),
            fee_value=fee_value,
            amount=admin_fee_amount,
            prize_pool_snapshot=prize_pool,
        )
        db.add(admin_fee)

    # Mark winning option
    winning_option.is_winner = True

    # Update bet status
    now = datetime.now(timezone.utc)
    bet.status = BetStatus.RESOLVED
    bet.resolved_at = now
    bet.chat_closes_at = now + timedelta(hours=2)

    await db.flush()
    logger.info(
        "Distributed prizes for bet %s: pool=%s, fee=%s, winners=%d",
        bet_id,
        prize_pool,
        admin_fee_amount,
        len(winners),
    )
