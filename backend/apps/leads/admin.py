from django.contrib import admin

from .models import Lead


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ("customer_name", "agency", "property", "status", "source_channel", "created_at")
    list_filter = ("status", "source_channel")
    search_fields = ("customer_name", "customer_email", "customer_phone", "agency__name")
    autocomplete_fields = ["agency", "property"]
    readonly_fields = ("created_at", "updated_at", "consent_timestamp", "referred_at")
