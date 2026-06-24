"""Celery Beat scheduler configuration.

Defines the periodic schedule for pipeline checks.  The beat schedule is set
directly on the shared `celery_app` instance so it's picked up by:
  - ``celery_beat_start.py`` (combined worker + beat)
  - ``celery -A app.celery_app beat`` (standalone beat)
  - ``celery -A app.celery_app worker --beat`` (embedded beat)
"""

from celery.schedules import crontab

from app.celery_app import celery_app

celery_app.conf.beat_schedule = {
    "scheduled-pipeline-check-every-15-min": {
        "task": "app.tasks.scheduler.scheduled_pipeline_check",
        "schedule": crontab(minute="*/15"),
    },
}

# Optional: human-readable timezone for the beat scheduler logs
celery_app.conf.timezone = "UTC"
