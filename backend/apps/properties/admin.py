from django.contrib import admin
from django.utils import timezone

from .models import PriceHistory, Property, PropertyImage


class PropertyImageInline(admin.TabularInline):
    model = PropertyImage
    extra = 0


class PriceHistoryInline(admin.TabularInline):
    model = PriceHistory
    extra = 0
    readonly_fields = ("price", "currency", "recorded_at")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class StaleListingFilter(admin.SimpleListFilter):
    title = "freshness"
    parameter_name = "freshness"

    def lookups(self, request, model_admin):
        return [("stale", "Stale / needs recheck"), ("never_checked", "Never checked")]

    def queryset(self, request, queryset):
        if self.value() == "stale":
            return queryset.filter(status=Property.ListingStatus.STALE)
        if self.value() == "never_checked":
            return queryset.filter(last_checked_at__isnull=True)
        return queryset


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "location",
        "property_type",
        "transaction_type",
        "price",
        "status",
        "verification_status",
        "agency",
        "last_seen_at",
    )
    list_filter = (StaleListingFilter, "status", "verification_status", "property_type", "transaction_type", "state")
    search_fields = ("title", "location", "city", "area", "source_property_id")
    readonly_fields = ("discovered_at", "created_at", "updated_at", "search_vector")
    inlines = [PropertyImageInline, PriceHistoryInline]
    actions = ["mark_stale", "mark_active", "mark_removed"]
    autocomplete_fields = ["agency"]

    fieldsets = (
        (None, {"fields": ("title", "description", "property_type", "transaction_type")}),
        ("Price", {"fields": ("price", "currency", "price_period")}),
        ("Location", {"fields": ("location", "state", "city", "area", "latitude", "longitude")}),
        ("Attributes", {"fields": ("bedrooms", "bathrooms", "toilets", "amenities", "furnished_status")}),
        ("Provenance", {"fields": ("agency", "source", "source_url", "source_property_id")}),
        ("Lifecycle", {"fields": ("status", "verification_status", "discovered_at", "last_checked_at", "last_seen_at")}),
        ("Visibility", {"fields": ("is_featured", "live_viewing_available")}),
    )

    @admin.action(description="Mark selected properties as STALE (needs recheck)")
    def mark_stale(self, request, queryset):
        queryset.update(status=Property.ListingStatus.STALE)

    @admin.action(description="Mark selected properties as ACTIVE (confirmed available)")
    def mark_active(self, request, queryset):
        now = timezone.now()
        queryset.update(status=Property.ListingStatus.ACTIVE, last_checked_at=now, last_seen_at=now)

    @admin.action(description="Mark selected properties as REMOVED")
    def mark_removed(self, request, queryset):
        queryset.update(status=Property.ListingStatus.REMOVED)
