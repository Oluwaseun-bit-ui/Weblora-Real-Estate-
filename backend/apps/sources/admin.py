from django.contrib import admin

from .models import PropertySource


@admin.register(PropertySource)
class PropertySourceAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "source_type",
        "ingestion_method",
        "permission_status",
        "is_active",
        "last_synced_at",
        "next_sync_at",
    )
    list_filter = ("source_type", "ingestion_method", "permission_status", "is_active")
    search_fields = ("name", "url", "contact_email")
    readonly_fields = ("last_synced_at",)
