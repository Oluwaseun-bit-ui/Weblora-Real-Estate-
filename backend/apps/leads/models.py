from django.db import models

from apps.agencies.models import Agency
from apps.core.models import TimeStampedModel
from apps.properties.models import Property


class Lead(TimeStampedModel):
    """
    A customer enquiry referred to an agency. The platform's core value
    proposition is connecting customers to agencies, not brokering the
    transaction itself -- so a Lead always makes clear it is being
    *referred*, not fulfilled, by the platform.
    """

    class Status(models.TextChoices):
        NEW = "NEW", "New"
        SENT = "SENT", "Sent to agency"
        CONTACTED = "CONTACTED", "Agency contacted customer"
        QUALIFIED = "QUALIFIED", "Qualified"
        CLOSED = "CLOSED", "Closed"
        INVALID = "INVALID", "Invalid"

    class SourceChannel(models.TextChoices):
        PROPERTY_ENQUIRY_FORM = "PROPERTY_ENQUIRY_FORM", "Property enquiry form"
        CALL_CLICK = "CALL_CLICK", "Call button click"
        EMAIL_CLICK = "EMAIL_CLICK", "Email button click"
        WHATSAPP_CLICK = "WHATSAPP_CLICK", "WhatsApp button click"
        AGENCY_WEBSITE_CLICK = "AGENCY_WEBSITE_CLICK", "Visit agency website click"
        LIVE_VIEWING_REQUEST = "LIVE_VIEWING_REQUEST", "Live viewing request"

    property = models.ForeignKey(Property, on_delete=models.SET_NULL, null=True, blank=True, related_name="leads")
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name="leads")

    # Minimal personal data collection (privacy-by-design): only what's
    # needed to route and follow up on the enquiry.
    customer_name = models.CharField(max_length=150)
    customer_email = models.EmailField(blank=True)
    customer_phone = models.CharField(max_length=32, blank=True)
    message = models.TextField(blank=True)

    source_channel = models.CharField(max_length=32, choices=SourceChannel.choices, default=SourceChannel.PROPERTY_ENQUIRY_FORM)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.NEW)

    consent_given = models.BooleanField(
        default=False, help_text="Customer consented to their contact details being shared with the agency."
    )
    consent_timestamp = models.DateTimeField(null=True, blank=True)

    referred_at = models.DateTimeField(null=True, blank=True, help_text="When the lead was actually sent to the agency.")

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status"]), models.Index(fields=["agency", "status"])]

    def __str__(self):
        return f"Lead from {self.customer_name} -> {self.agency.name} ({self.status})"
