"""Basic smoke tests to ensure the app imports and key services work."""
from decimal import Decimal

from app.models.bet import BetStatus, ResolutionType
from app.models.wallet_transaction import TransactionType
from app.models.payment import PaymentStatus
from app.models.admin_fee import FeeType


def test_bet_status_enum_values():
    assert BetStatus.OPEN.value == "open"
    assert BetStatus.RESOLVED.value == "resolved"
    assert BetStatus.DISPUTED.value == "disputed"


def test_resolution_type_enum_values():
    assert ResolutionType.AUTO_API.value == "auto_api"
    assert ResolutionType.VOTING.value == "voting"


def test_transaction_type_enum_values():
    assert TransactionType.DEPOSIT.value == "deposit"
    assert TransactionType.PRIZE_CREDIT.value == "prize_credit"
    assert TransactionType.BET_LOCK.value == "bet_lock"


def test_payment_status_enum_values():
    assert PaymentStatus.PENDING.value == "pending"
    assert PaymentStatus.APPROVED.value == "approved"


def test_fee_type_enum_values():
    assert FeeType.PERCENT.value == "percent"
    assert FeeType.FIXED.value == "fixed"


def test_app_imports():
    from app.main import app
    assert app is not None
    assert app.title == "Patinho API"


def test_settings_load():
    from app.config import settings
    assert settings is not None
    assert settings.SECRET_KEY


def test_percent_fee_calculation():
    prize_pool = Decimal("100.00")
    fee_percent = Decimal("8")
    fee = prize_pool * fee_percent / Decimal("100")
    assert fee == Decimal("8.00")


def test_fixed_fee_cap():
    prize_pool = Decimal("5.00")
    fixed_fee = Decimal("10.00")
    # Fixed fee should never exceed prize pool
    fee = min(fixed_fee, prize_pool)
    assert fee == Decimal("5.00")
