from django.core.management.base import BaseCommand, CommandError

from apps.sources.models import PropertySource
from apps.sources.services import sync_source


class Command(BaseCommand):
    help = "Sync listings now from every active, authorized source with an adapter (or just --source NAME)."

    def add_arguments(self, parser):
        parser.add_argument("--source", help="Only sync the source with this name (case-insensitive).")

    def handle(self, *args, **options):
        sources = PropertySource.objects.filter(
            is_active=True, permission_status=PropertySource.PermissionStatus.AUTHORIZED
        ).exclude(adapter="")
        if options["source"]:
            sources = sources.filter(name__iexact=options["source"])
        if not sources:
            raise CommandError("No matching active, authorized source with an adapter.")

        for source in sources:
            self.stdout.write(f"Syncing {source.name}… (this can take several minutes on the first run)")
            result = sync_source(source)
            self.stdout.write(
                self.style.SUCCESS(
                    f"{source.name}: {result.created} new, {result.updated} updated, "
                    f"{result.marked_stale} marked stale, {result.agencies_created} new agents, {result.errors} errors"
                )
            )
