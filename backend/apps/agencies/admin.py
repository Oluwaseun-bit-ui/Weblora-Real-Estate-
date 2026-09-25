from django.contrib import admin
from django.utils import timezone

from apps.core.models import log_action

from .models import Agency


class VerificationStatusFilter(admin.SimpleListFilter):
    title = "verification queue"
    parameter_name = "queue"

    def lookups(self, request, model_admin):
        return [("needs_review", "Needs review (discovered/pending/in progress)"), ("recheck_due", "Recheck due")]

    def queryset(self, request, queryset):
        if self.value() == "needs_review":
            return queryset.filter(
                verification_status__in=[
                    Agency.VerificationStatus.DISCOVERED,
                    Agency.VerificationStatus.PENDING_REVIEW,
                    Agency.VerificationStatus.VERIFICATION_IN_PROGRESS,
                ]
            )
        if self.value() == "recheck_due":
            return queryset.filter(verification_recheck_date__lte=timezone.localdate())
        return queryset


@admin.register(Agency)
class AgencyAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "verification_status",
        "phone_status",
        "email_status",
        "website_status",
        "is_suspended",
        "verification_recheck_date",
    )
    list_filter = (VerificationStatusFilter, "verification_status", "is_suspended")
    search_fields = ("name", "email", "phone_number", "cac_registration_number", "esvarbon_registration_number", "lasrera_registration_number")
    readonly_fields = ("slug", "created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("name", "slug", "description", "logo", "logo_display_authorized")}),
        ("Contact", {"fields": ("website", "phone_number", "email", "whatsapp_number", "business_address", "service_locations")}),
        (
            "Contact verification",
            {"fields": ("phone_status", "email_status", "website_status")},
        ),
        (
            "Regulatory identity",
            {"fields": ("cac_registration_number", "esvarbon_registration_number", "lasrera_registration_number")},
        ),
        ("Verification status", {"fields": ("verification_status", "verification_recheck_date")}),
        ("Suspension", {"fields": ("is_suspended", "suspension_reason")}),
        ("Sources", {"fields": ("sources",)}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )
    actions = ["mark_pending_review", "mark_verified", "mark_rejected", "mark_suspended"]

    def save_model(self, request, obj, form, change):
        previous = None
        if change:
            previous = Agency.objects.get(pk=obj.pk).verification_status
        super().save_model(request, obj, form, change)
        if previous is not None and previous != obj.verification_status:
            log_action(
                actor=request.user,
                action="agency.verification_status_changed",
                obj=obj,
                previous_value={"verification_status": previous},
                new_value={"verification_status": obj.verification_status},
            )

    def _transition(self, request, queryset, new_status, notes):
        for agency in queryset:
            previous = agency.verification_status
            if new_status == Agency.VerificationStatus.VERIFIED and not agency.has_sufficient_contact_info:
                self.message_user(
                    request,
                    f"Skipped {agency.name}: insufficient verified contact information for VERIFIED status.",
                    level="warning",
                )
                continue
            agency.verification_status = new_status
            agency.save(update_fields=["verification_status", "updated_at"])
            log_action(
                actor=request.user,
                action="agency.verification_status_changed",
                obj=agency,
                previous_value={"verification_status": previous},
                new_value={"verification_status": new_status},
                notes=notes,
            )

    @admin.action(description="Mark selected agencies as PENDING_REVIEW")
    def mark_pending_review(self, request, queryset):
        self._transition(request, queryset, Agency.VerificationStatus.PENDING_REVIEW, "Bulk action via admin")

    @admin.action(description="Mark selected agencies as VERIFIED (requires sufficient verified contact info)")
    def mark_verified(self, request, queryset):
        self._transition(request, queryset, Agency.VerificationStatus.VERIFIED, "Bulk action via admin")

    @admin.action(description="Mark selected agencies as REJECTED")
    def mark_rejected(self, request, queryset):
        self._transition(request, queryset, Agency.VerificationStatus.REJECTED, "Bulk action via admin")

    @admin.action(description="Suspend selected agencies")
    def mark_suspended(self, request, queryset):
        for agency in queryset:
            previous = agency.verification_status
            agency.is_suspended = True
            agency.verification_status = Agency.VerificationStatus.SUSPENDED
            agency.save(update_fields=["is_suspended", "verification_status", "updated_at"])
            log_action(
                actor=request.user,
                action="agency.suspended",
                obj=agency,
                previous_value={"verification_status": previous},
                new_value={"verification_status": Agency.VerificationStatus.SUSPENDED},
            )
