from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

# Register signal handlers for automatic task metrics recording
import app.workers.celery_signals  # noqa: F401, E402

celery_app = Celery(
    "retailflux",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.workers.tasks.process_upload",
        "app.workers.tasks.forecast_tasks",
        "app.workers.tasks.insight_tasks",
        "app.workers.tasks.alert_tasks",
        "app.workers.tasks.task_sla",
        "app.workers.tasks.task_ai_recommendations",
        "app.workers.tasks.inventory_nightly",
        "app.workers.tasks.inventory_advanced",
        "app.workers.tasks.embeddings_backfill",
        "app.workers.tasks.pricing_weekly",
        "app.workers.tasks.task_digest",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    beat_schedule={
        "nightly-insights": {
            "task": "app.workers.tasks.insight_tasks.generate_nightly_insights",
            "schedule": crontab(hour=2, minute=0),  # 02:00 UTC daily
        },
        "nightly-forecasts": {
            "task": "app.workers.tasks.forecast_tasks.refresh_nightly_forecasts",
            "schedule": crontab(hour=3, minute=0),  # 03:00 UTC daily
        },
        "hourly-alerts": {
            "task": "app.workers.tasks.alert_tasks.periodic_alert_check",
            "schedule": crontab(minute=0),  # top of every hour
        },
        "hourly-task-sla": {
            "task": "app.workers.tasks.task_sla.task_sla_sweep",
            "schedule": crontab(minute=5),  # 5 min past every hour
        },
        "hourly-ai-recommendations": {
            "task": "app.workers.tasks.task_ai_recommendations.task_recommendation_sweep",
            "schedule": crontab(minute=15),  # 15 min past every hour
        },
        "hourly-task-escalation": {
            "task": "app.workers.tasks.task_ai_recommendations.task_escalation_sweep",
            "schedule": crontab(minute=30),  # 30 min past every hour
        },
        "daily-productivity-rollup": {
            "task": "app.workers.tasks.task_ai_recommendations.task_productivity_rollup",
            "schedule": crontab(hour=4, minute=0),  # 04:00 UTC daily
        },
        "weekly-task-digest": {
            "task": "app.workers.tasks.task_ai_recommendations.task_weekly_digest",
            "schedule": crontab(hour=8, minute=0, day_of_week=1),  # Monday 08:00 UTC
        },
        "inventory-nightly": {
            "task": "app.workers.tasks.inventory_nightly.inventory_nightly_recompute",
            "schedule": crontab(hour=2, minute=30),  # 02:30 UTC daily
        },
        "inventory-reorder-refresh": {
            "task": "app.workers.tasks.inventory_advanced.inventory_reorder_refresh",
            "schedule": crontab(minute=45),  # hourly at :45
        },
        "inventory-anomaly-scan": {
            "task": "app.workers.tasks.inventory_advanced.inventory_anomaly_scan",
            "schedule": crontab(minute=0, hour="*/6"),  # every 6 hours
        },
        "inventory-health-score": {
            "task": "app.workers.tasks.inventory_advanced.inventory_health_score_refresh",
            "schedule": crontab(hour=2, minute=45),  # 02:45 UTC daily
        },
        "weekly-embeddings-backfill": {
            "task": "app.workers.tasks.embeddings_backfill.embeddings_backfill_all",
            "schedule": crontab(hour=5, minute=0, day_of_week=0),  # Sunday 05:00 UTC
        },
        "weekly-pricing-suggestions": {
            "task": "app.workers.tasks.pricing_weekly.pricing_suggestions_refresh",
            "schedule": crontab(hour=3, minute=0, day_of_week=1),  # Monday 03:00 UTC
        },
        "daily-task-digest": {
            "task": "app.workers.tasks.task_digest.daily_task_digest",
            "schedule": crontab(hour=7, minute=0),  # 07:00 UTC daily
        },
    },
)
