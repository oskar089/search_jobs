"""Start a Celery worker + Beat scheduler together in a single process.

Usage:
    python celery_beat_start.py

Equivalent to:
    celery -A app.celery_app worker --pool=solo --beat --loglevel=info

The important difference is that this script imports ``app.celery_beat``
**before** starting the worker, which configures the periodic schedule on
``celery_app`` so that the embedded beat scheduler knows what to run.
"""

from app.celery_app import celery_app

# Import AFTER celery_app so we can configure the beat schedule on it.
# The module-level code in celery_beat.py sets
#     celery_app.conf.beat_schedule = { ... }
# which is read by the beat scheduler at startup.
import app.celery_beat  # noqa: F401, E402 — loads beat schedule onto celery_app

if __name__ == "__main__":
    celery_app.start(argv=[
        "celery",
        "-A", "app.celery_app",
        "worker",
        "--pool=solo",
        "--beat",
        "--loglevel=info",
    ])
