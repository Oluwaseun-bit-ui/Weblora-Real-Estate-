import secrets

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.agencies.models import Agency
from apps.core.models import TimeStampedModel
from apps.properties.models import Property


class AgencyRepresentative(TimeStampedModel):
    """
    Controlled, MVP-friendly way to authenticate the human who will conduct
    a live viewing on behalf of an agency, without requiring agencies to
    have full platform accounts. For the MVP an administrator assigns a
    representative (name + contact) to an agency; that representative gets
    a short-lived, single-use secure invitation link per live viewing
    session rather than a standing account/password.
    """

    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name="representatives")
    name = models.CharField(max_length=150)
    phone_number = models.CharField(max_length=32, blank=True)
    email = models.EmailField(blank=True)
    is_active = models.BooleanField(default=True)
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.agency.name})"


def generate_token():
    return secrets.token_urlsafe(32)


class LiveViewingRequest(TimeStampedModel):
    class Status(models.TextChoices):
        REQUESTED = "REQUESTED", "Requested"
        PENDING_AGENT = "PENDING_AGENT", "Pending agent"
        ACCEPTED = "ACCEPTED", "Accepted"
        SCHEDULED = "SCHEDULED", "Scheduled"
        LIVE = "LIVE", "Live"
        COMPLETED = "COMPLETED", "Completed"
        DECLINED = "DECLINED", "Declined"
        CANCELLED = "CANCELLED", "Cancelled"
        NO_SHOW = "NO_SHOW", "No show"
        FAILED = "FAILED", "Failed"

    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="live_viewing_requests")
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name="live_viewing_requests")
    representative = models.ForeignKey(
        AgencyRepresentative, on_delete=models.SET_NULL, null=True, blank=True, related_name="live_viewing_requests"
    )

    # Minimal customer data -- no account required to request a viewing.
    customer_name = models.CharField(max_length=150)
    customer_email = models.EmailField(blank=True)
    customer_phone = models.CharField(max_length=32, blank=True)

    requested_date = models.DateField()
    requested_time = models.TimeField(null=True, blank=True, help_text="Blank means 'earliest available'.")
    customer_message = models.TextField(blank=True)

    status = models.CharField(max_length=16, choices=Status.choices, default=Status.REQUESTED)

    accepted_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    decline_reason = models.TextField(blank=True)

    # Short-lived customer access token for joining the room -- never a
    # permanent/public link. Regenerated per session by the video provider
    # layer; this token only gates *entry to the booking*, the actual media
    # room credential is minted at join time (see providers.base).
    customer_access_token = models.CharField(max_length=64, unique=True, default=generate_token, editable=False)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status"]), models.Index(fields=["agency", "status"])]

    def __str__(self):
        return f"Live viewing: {self.property} for {self.customer_name} ({self.status})"


class LiveViewingSession(TimeStampedModel):
    class Status(models.TextChoices):
        SCHEDULED = "SCHEDULED", "Scheduled"
        LIVE = "LIVE", "Live"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"
        CANCELLED = "CANCELLED", "Cancelled"

    viewing_request = models.OneToOneField(LiveViewingRequest, on_delete=models.CASCADE, related_name="session")

    # Provider abstraction fields -- the backend never talks raw WebRTC; it
    # asks the configured provider (LiveKit/Agora/Daily/Twilio/...) to
    # create a room and mint short-lived tokens. `provider_name` +
    # `provider_room_id` are all that's needed to reconstruct a session
    # against whichever provider is configured.
    provider_name = models.CharField(
        max_length=32,
        blank=True,
        help_text="Which real-time video provider (livekit/agora/daily/twilio) backs this session.",
    )
    provider_room_id = models.CharField(max_length=255, blank=True)

    scheduled_start = models.DateTimeField()
    scheduled_end = models.DateTimeField()
    actual_start = models.DateTimeField(null=True, blank=True)
    actual_end = models.DateTimeField(null=True, blank=True)

    status = models.CharField(max_length=16, choices=Status.choices, default=Status.SCHEDULED)

    # No automatic recording by default (privacy-by-design). If recording
    # is ever introduced, it must be opt-in with recorded consent.
    recording_enabled = models.BooleanField(default=False)
    consent_recorded_at = models.DateTimeField(null=True, blank=True)

    participant_info = models.JSONField(
        default=dict, blank=True, help_text="Non-sensitive join metadata, e.g. join/leave timestamps per role."
    )

    class Meta:
        ordering = ["-scheduled_start"]

    def __str__(self):
        return f"Session for {self.viewing_request} ({self.status})"


class LiveViewingEvent(TimeStampedModel):
    """
    Audit trail for a live viewing's lifecycle (separate from the generic
    AuditLog so operational dashboards can query it cheaply): request
    created, accepted, declined, started, ended, no-show, reconnect, etc.
    """

    viewing_request = models.ForeignKey(LiveViewingRequest, on_delete=models.CASCADE, related_name="events")
    event_type = models.CharField(max_length=50)
    detail = models.JSONField(default=dict, blank=True)
    occurred_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["occurred_at"]
