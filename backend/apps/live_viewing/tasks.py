from celery import shared_task

from .services import mark_no_shows


@shared_task
def mark_no_shows_task():
    """Run every few minutes via Celery beat: CELERY_BEAT_SCHEDULE in config.settings (add when beat is set up)."""
    mark_no_shows()
