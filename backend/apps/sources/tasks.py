from celery import shared_task

from .services import sync_due_sources


@shared_task
def sync_due_sources_task():
    """Nightly via Celery beat (CELERY_BEAT_SCHEDULE in config.settings)."""
    return {name: vars(result) for name, result in sync_due_sources().items()}
