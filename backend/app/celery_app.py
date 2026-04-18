from celery import Celery
from celery.schedules import crontab

from app.config import settings

celery_app = Celery(
    "patinho",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="America/Sao_Paulo",
    enable_utc=True,
    beat_schedule={
        "check_sports_results": {
            "task": "app.tasks.sports.check_sports_results",
            "schedule": 300.0,  # every 5 minutes
        },
        "check_voting_consensus_all": {
            "task": "app.tasks.voting.check_voting_consensus_all",
            "schedule": 600.0,  # every 10 minutes
        },
        "check_expired_disputes": {
            "task": "app.tasks.disputes.check_expired_disputes",
            "schedule": 1800.0,  # every 30 minutes
        },
        "expire_pending_payments": {
            "task": "app.tasks.payments.expire_pending_payments",
            "schedule": 900.0,  # every 15 minutes
        },
        "lock_expired_bets": {
            "task": "app.tasks.betting.lock_expired_bets",
            "schedule": 60.0,  # every 1 minute
        },
        "auto_resolve_pending_confirmations": {
            "task": "app.tasks.confirmation.auto_resolve_pending_confirmations",
            "schedule": 600.0,  # every 10 minutes
        },
        "reset_weekly_ranking": {
            "task": "app.tasks.ranking.reset_weekly_ranking",
            "schedule": crontab(minute="0", hour="0", day_of_week="1"),  # Monday 00:00
        },
    },
)

celery_app.autodiscover_tasks(["app.tasks"])
