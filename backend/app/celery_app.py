from celery import Celery

from app.config import settings

celery_app = Celery(
    "search_jobs",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.task_serializer = "json"
celery_app.conf.result_serializer = "json"
celery_app.conf.accept_content = ["json"]
celery_app.conf.task_track_started = True
celery_app.conf.task_ignore_result = False

# Import task modules so Celery registers them
import app.tasks.apply  # noqa: E402, F401
import app.tasks.match  # noqa: E402, F401
import app.tasks.notify  # noqa: E402, F401
import app.tasks.orchestrator  # noqa: E402, F401
import app.tasks.scrape  # noqa: E402, F401
