from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "actor", "action", "object_type", "object_id")
    list_filter = ("action", "object_type")
    search_fields = ("object_id", "notes", "actor__email")
    readonly_fields = [f.name for f in AuditLog._meta.fields]
    date_hierarchy = "timestamp"

    def has_add_permission(self, request):
        # Audit entries are only ever written by application code.
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
