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
    # Worker listens on default,payments,resolution,notifications (see
    # docker-compose celery_worker command). Without this, beat publishes
    # tasks to the celery default queue ("celery"), the worker never sees
    # them, and scheduled jobs (lock_expired_bets, etc.) silently pile up.
    task_default_queue="default",
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
        "reconcile_pending_payments": {
            "task": "app.tasks.payments.reconcile_pending_payments",
            "schedule": 60.0,  # every 1 minute — fallback when MP webhook can't reach us
        },
        "lock_expired_bets": {
            "task": "app.tasks.betting.lock_expired_bets",
            "schedule": 60.0,  # every 1 minute
        },
        "refund_stale_locked_bets": {
            "task": "app.tasks.betting.refund_stale_locked_bets",
            "schedule": crontab(minute="0", hour="3"),  # daily 03:00
        },
        "auto_resolve_pending_confirmations": {
            "task": "app.tasks.confirmation.auto_resolve_pending_confirmations",
            "schedule": 600.0,  # every 10 minutes
        },
        "reset_weekly_ranking": {
            "task": "app.tasks.ranking.reset_weekly_ranking",
            "schedule": crontab(minute="0", hour="0", day_of_week="1"),  # Monday 00:00
        },
        "check_tournament_matches": {
            "task": "app.tasks.tournament.check_tournament_matches",
            "schedule": 300.0,  # every 5 minutes, aligned with API-Football fixture query cadence
        },
    },
)

celery_app.autodiscover_tasks(["app.tasks"])
