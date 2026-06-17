from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

celery_app = Celery(
    "kissanbot_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.worker.tasks", "app.worker.cron_tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
)

# Celery Beat Schedule
celery_app.conf.beat_schedule = {
    'daily-weather-alert-check': {
        'task': 'app.worker.cron_tasks.check_weather_and_alert',
        # Run every day at 6:00 AM (UTC) -> 11:30 AM IST
        'schedule': crontab(hour=6, minute=0),
    },
    'health-metrics-monitor': {
        'task': 'app.worker.cron_tasks.monitor_health_metrics',
        # Run every 5 minutes
        'schedule': crontab(minute='*/5'),
    },
}
