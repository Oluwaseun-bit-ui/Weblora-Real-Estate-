from django.contrib import admin

from .models import RegulatoryRecord, VerificationCheck


@admin.register(VerificationCheck)
class VerificationCheckAdmin(admin.ModelAdmin):
    list_display = ("agency", "check_type", "method", "result", "checked_at", "checked_by", "recheck_date")
    list_filter = ("check_type", "method", "result")
    search_fields = ("agency__name", "registration_number", "subject_name")
    autocomplete_fields = ["agency"]
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "checked_at"

    fieldsets = (
        (None, {"fields": ("agency", "check_type", "method", "source", "result")}),
        ("Subject", {"fields": ("registration_number", "subject_name")}),
        ("Evidence", {"fields": ("evidence_reference", "evidence_file", "notes")}),
        ("Timing", {"fields": ("checked_at", "checked_by", "expiration_date", "recheck_date")}),
    )

    def save_model(self, request, obj, form, change):
        if not obj.checked_by_id:
            obj.checked_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(RegulatoryRecord)
class RegulatoryRecordAdmin(admin.ModelAdmin):
    list_display = ("regulator", "registration_number", "subject_name", "status_on_registry", "checked_at")
    list_filter = ("regulator",)
    search_fields = ("registration_number", "subject_name")
