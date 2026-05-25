import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bet import Bet, BetStatus
from app.models.bet_option import BetOption
from app.services.distribution_service import distribute_prizes

logger = logging.getLogger(__name__)


async def resolve_sports_bet(db: AsyncSession, bet_id: UUID) -> bool:
    """
    Resolve a sports bet using the relevant upstream API.

    Dispatches by bet.template (None is treated as match_winner for
    backwards compatibility with bets created before the template column
    was introduced). Called by a Celery task once an event has finished.

    Returns True if resolved, False if not yet finished.
    """
    from app.integrations.api_f1 import api_f1_client
    from app.integrations.api_futebol import api_futebol_client
    from app.integrations.api_tennis import api_tennis_client

    bet = await db.get(Bet, bet_id)
    if not bet:
        logger.warning("Bet %s not found for sports resolution", bet_id)
        return False

    if bet.status != BetStatus.LOCKED:
        logger.warning(
            "Bet %s is not locked (status=%s), skipping", bet_id, bet.status
        )
        return False

    if not bet.sports_match_id:
        logger.warning("Bet %s has no sports_match_id", bet_id)
        return False

    # Load options once — every branch needs them
    result = await db.execute(
        select(BetOption).where(BetOption.bet_id == bet_id)
    )
    options = list(result.scalars().all())

    template = bet.template or "match_winner"

    if template == "match_winner":
        fixture_result = await api_futebol_client.get_fixture_result(
            bet.sports_match_id
        )
        if fixture_result is None:
            return False

        winner_label = fixture_result.get("winner")  # team name or "Empate"
        winning_option: BetOption | None = None

        if winner_label:
            for opt in options:
                if opt.label.lower() == winner_label.lower():
                    winning_option = opt
                    break
            if not winning_option:
                for opt in options:
                    if winner_label.lower() in opt.label.lower():
                        winning_option = opt
                        break

        if not winning_option:
            logger.error(
                "Could not map winner '%s' to any option for bet %s. Options: %s",
                winner_label,
                bet_id,
                [o.label for o in options],
            )
            return False

        await distribute_prizes(db, bet_id, winning_option.id)
        logger.info(
            "Resolved match_winner bet %s with option %s",
            bet_id,
            winning_option.id,
        )
        return True

    if template == "exact_score":
        fixture_result = await api_futebol_client.get_fixture_result(
            bet.sports_match_id
        )
        if fixture_result is None:
            return False

        home_score = fixture_result.get("home_score", 0)
        away_score = fixture_result.get("away_score", 0)
        target = f"{home_score}x{away_score}"

        winning_option = next(
            (o for o in options if o.label == target), None
        )
        if not winning_option:
            # Fallback bucket for any score not in the preset list
            winning_option = next(
                (o for o in options if o.label == "Outro"), None
            )

        if not winning_option:
            logger.error(
                "exact_score resolution: no matching option for %s in bet %s. Options: %s",
                target,
                bet_id,
                [o.label for o in options],
            )
            return False

        await distribute_prizes(db, bet_id, winning_option.id)
        logger.info(
            "Resolved exact_score bet %s: score=%s option=%s",
            bet_id,
            target,
            winning_option.id,
        )
        return True

    if template == "f1_winner":
        winner_name = await api_f1_client.get_race_winner(bet.sports_match_id)
        if not winner_name:
            return False

        winning_option = next(
            (o for o in options if o.label.lower() == winner_name.lower()),
            None,
        )
        if not winning_option:
            # Try matching on last-name (common F1 driver rendering)
            parts = winner_name.split()
            last = parts[-1].lower() if parts else ""
            if last:
                winning_option = next(
                    (o for o in options if last in o.label.lower()), None
                )

        if not winning_option:
            logger.error(
                "Could not map F1 winner '%s' to any option for bet %s. Options: %s",
                winner_name,
                bet_id,
                [o.label for o in options],
            )
            return False

        await distribute_prizes(db, bet_id, winning_option.id)
        logger.info(
            "Resolved f1_winner bet %s with option %s (winner=%s)",
            bet_id,
            winning_option.id,
            winner_name,
        )
        return True

    if template == "tennis_winner":
        winner_name = await api_tennis_client.get_match_winner(bet.sports_match_id)
        if not winner_name:
            return False

        winning_option = next(
            (o for o in options if o.label.lower() == winner_name.lower()),
            None,
        )
        if not winning_option:
            # Try matching on last-name (tennis players are often rendered as
            # "N. Djokovic" or "Djokovic N." etc.)
            parts = winner_name.split()
            last = parts[-1].lower() if parts else ""
            if last:
                winning_option = next(
                    (o for o in options if last in o.label.lower()), None
                )
            # Try first part as well (e.g. surname-first renderings)
            if not winning_option and parts:
                first = parts[0].lower()
                winning_option = next(
                    (o for o in options if first in o.label.lower()), None
                )

        if not winning_option:
            logger.error(
                "Could not map tennis winner '%s' to any option for bet %s. Options: %s",
                winner_name,
                bet_id,
                [o.label for o in options],
            )
            return False

        await distribute_prizes(db, bet_id, winning_option.id)
        logger.info(
            "Resolved tennis_winner bet %s with option %s (winner=%s)",
            bet_id,
            winning_option.id,
            winner_name,
        )
        return True

    logger.error(
        "Unknown template '%s' for bet %s; cannot resolve",
        template,
        bet_id,
    )
    return False


async def check_voting_consensus(db: AsyncSession, bet_id: UUID) -> bool:
    """
    Decide whether a voting-phase bet can be resolved now.

    Two paths to resolution:
      1. **Early 70% supermajority**: any single option has >=70% of total
         participant votes — resolves immediately even before everyone voted.
      2. **Full turnout simple majority**: every participant has voted and
         one option has strictly more votes than the next best — resolves
         with a simple majority. Tie → no resolution (falls through to the
         24h timeout which escalates to dispute).

    Returns True if the bet was resolved.
    """
    from app.models.participation import Participation
    from app.models.vote import Vote

    bet = await db.get(Bet, bet_id)
    if not bet:
        return False

    if bet.status != BetStatus.VOTING:
        return False

    # Count total participants
    part_result = await db.execute(
        select(Participation).where(Participation.bet_id == bet_id)
    )
    participations = list(part_result.scalars().all())
    total_participants = len(participations)

    if total_participants == 0:
        return False

    # Count votes per option
    vote_result = await db.execute(
        select(Vote).where(Vote.bet_id == bet_id)
    )
    votes = list(vote_result.scalars().all())
    total_votes = len(votes)

    vote_counts: dict[UUID, int] = {}
    for vote in votes:
        vote_counts[vote.bet_option_id] = vote_counts.get(vote.bet_option_id, 0) + 1

    # Path 1: 70% supermajority of participants
    threshold = 0.70
    for option_id, count in vote_counts.items():
        ratio = count / total_participants
        if ratio >= threshold:
            await distribute_prizes(db, bet_id, option_id)
            logger.info(
                "Voting consensus (supermajority) for bet %s: option %s with %.1f%%",
                bet_id, option_id, ratio * 100,
            )
            return True

    # Path 2: full turnout → simple majority (but not a tie)
    if total_votes >= total_participants and vote_counts:
        sorted_counts = sorted(vote_counts.items(), key=lambda kv: kv[1], reverse=True)
        top_option, top_count = sorted_counts[0]
        second_count = sorted_counts[1][1] if len(sorted_counts) > 1 else 0
        if top_count > second_count:
            await distribute_prizes(db, bet_id, top_option)
            logger.info(
                "Voting consensus (full turnout majority) for bet %s: option %s with %d/%d",
                bet_id, top_option, top_count, total_participants,
            )
            return True

    return False
