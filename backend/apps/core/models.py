import uuid

from django.conf import settings
from django.db import models


class TimeStampedModel(models.Model):
    """Base model with UUID pk and created/updated timestamps."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class AuditLog(models.Model):
    """
    Records every important verification / admin action so decisions
    (approve/reject an agency, mark a property verified, etc.) are
    auditable after the fact.
    """

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_entries",
        help_text="Admin/staff user who performed the action. Null for system/automated actions.",
    )
    action = models.CharField(max_length=100, help_text="e.g. 'agency.verified', 'property.status_changed'")

    # Generic reference to the affected object, kept simple (string type +
    # id) rather than django.contrib.contenttypes to avoid coupling every
    # app to a single generic FK pattern this early.
    object_type = models.CharField(max_length=100, help_text="e.g. 'Agency', 'Property', 'VerificationCheck'")
    object_id = models.CharField(max_length=64)

    previous_value = models.JSONField(null=True, blank=True)
    new_value = models.JSONField(null=True, blank=True)
    notes = models.TextField(blank=True)

    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["object_type", "object_id"]),
            models.Index(fields=["action"]),
        ]

    def __str__(self):
        return f"{self.action} on {self.object_type}:{self.object_id} at {self.timestamp:%Y-%m-%d %H:%M}"


def log_action(*, actor, action, obj, previous_value=None, new_value=None, notes=""):
    """Convenience helper used across apps to write a consistent audit entry."""
    return AuditLog.objects.create(
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        action=action,
        object_type=obj.__class__.__name__,
        object_id=str(obj.pk),
        previous_value=previous_value,
        new_value=new_value,
        notes=notes,
    )
