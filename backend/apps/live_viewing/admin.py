from django.contrib import admin

from .models import AgencyRepresentative, LiveViewingEvent, LiveViewingRequest, LiveViewingSession


class LiveViewingSessionInline(admin.StackedInline):
    model = LiveViewingSession
    extra = 0
    readonly_fields = ("provider_room_id", "actual_start", "actual_end")


class LiveViewingEventInline(admin.TabularInline):
    model = LiveViewingEvent
    extra = 0
    readonly_fields = ("event_type", "detail", "occurred_at")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(LiveViewingRequest)
class LiveViewingRequestAdmin(admin.ModelAdmin):
    list_display = ("property", "customer_name", "agency", "representative", "status", "requested_date", "requested_time")
    list_filter = ("status",)
    search_fields = ("customer_name", "customer_email", "property__title", "agency__name")
    autocomplete_fields = ["property", "agency", "representative"]
    readonly_fields = ("customer_access_token", "accepted_at", "started_at", "ended_at", "created_at", "updated_at")
    inlines = [LiveViewingSessionInline, LiveViewingEventInline]


@admin.register(AgencyRepresentative)
class AgencyRepresentativeAdmin(admin.ModelAdmin):
    list_display = ("name", "agency", "phone_number", "email", "is_active")
    search_fields = ("name", "agency__name", "email", "phone_number")
    autocomplete_fields = ["agency"]


@admin.register(LiveViewingSession)
class LiveViewingSessionAdmin(admin.ModelAdmin):
    list_display = ("viewing_request", "provider_name", "status", "scheduled_start", "scheduled_end")
    list_filter = ("status", "provider_name")
    readonly_fields = ("provider_room_id",)
