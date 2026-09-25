from django.contrib import admin, messages

from .models import PropertySource
from .services import sync_source


@admin.register(PropertySource)
class PropertySourceAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "source_type",
        "ingestion_method",
        "adapter",
        "permission_status",
        "is_active",
        "last_synced_at",
        "next_sync_at",
    )
    list_filter = ("source_type", "ingestion_method", "permission_status", "is_active")
    search_fields = ("name", "url", "contact_email")
    readonly_fields = ("last_synced_at",)
    actions = ["sync_now"]

    @admin.action(description="Sync listings now (can take several minutes)")
    def sync_now(self, request, queryset):
        for source in queryset.exclude(adapter=""):
            try:
                result = sync_source(source)
            except Exception as exc:
                self.message_user(request, f"{source.name}: sync failed — {exc}", level=messages.ERROR)
                continue
            self.message_user(
                request,
                f"{source.name}: {result.created} new, {result.updated} updated, "
                f"{result.marked_stale} marked stale, {result.errors} errors",
            )
