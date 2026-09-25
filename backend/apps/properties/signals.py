from django.contrib.postgres.search import SearchVector
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Property


@receiver(post_save, sender=Property)
def update_search_vector(sender, instance, **kwargs):
    """
    Keeps Property.search_vector in sync so `q=` free-text search works.
    A signal (rather than a DB trigger) keeps this portable for the MVP;
    if search volume grows, replace with a Postgres trigger or move to
    Elasticsearch/OpenSearch per the search-engine design note in the
    architecture doc -- nothing else in the codebase depends on how the
    vector gets populated.
    """
    # Avoid recursion: only update the column itself via a queryset update.
    Property.objects.filter(pk=instance.pk).update(
        search_vector=(
            SearchVector("title", weight="A")
            + SearchVector("location", weight="A")
            + SearchVector("city", weight="B")
            + SearchVector("area", weight="B")
            + SearchVector("description", weight="C")
        )
    )
