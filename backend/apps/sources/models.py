from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import TimeStampedModel


class PropertySource(TimeStampedModel):
    """
    Where property/agency data comes from. Every ingested Property and every
    discovered Agency links back to the source(s) it came from, so we can
    always answer "why is this listing on the platform" and respect each
    source's terms.

    This is deliberately NOT a scraper-config model. `ingestion_method`
    constrains what's allowed, and `permission_status` must be authorized
    before a source can be set active.
    """

    class SourceType(models.TextChoices):
        AGENCY_PARTNER_API = "AGENCY_PARTNER_API", "Agency/Agency-network partner API"
        REGULATORY_REGISTRY = "REGULATORY_REGISTRY", "Regulatory body public registry"
        LISTING_PARTNER_FEED = "LISTING_PARTNER_FEED", "Authorized listing partner feed"
        MANUAL = "MANUAL", "Manual entry (admin/ops)"
        PUBLIC_DATA = "PUBLIC_DATA", "Permitted public dataset"

    class IngestionMethod(models.TextChoices):
        API = "API", "API integration"
        AUTHORIZED_FEED = "AUTHORIZED_FEED", "Authorized feed (RSS/XML/CSV export etc.)"
        PARTNER_FEED = "PARTNER_FEED", "Partner feed under agreement"
        MANUAL_ENTRY = "MANUAL_ENTRY", "Manual entry by admin/ops"
        PERMITTED_PUBLIC_DATA = "PERMITTED_PUBLIC_DATA", "Permitted public data (e.g. open registry)"
        APPROVED_METADATA = "APPROVED_METADATA", "Approved public page metadata (structured data the source publishes for reuse)"

    class PermissionStatus(models.TextChoices):
        PENDING_REVIEW = "PENDING_REVIEW", "Pending legal/ops review"
        AUTHORIZED = "AUTHORIZED", "Authorized"
        REVOKED = "REVOKED", "Revoked"
        NOT_AUTHORIZED = "NOT_AUTHORIZED", "Not authorized (do not ingest)"

    name = models.CharField(max_length=255)
    url = models.URLField(blank=True)
    source_type = models.CharField(max_length=32, choices=SourceType.choices)
    ingestion_method = models.CharField(max_length=32, choices=IngestionMethod.choices)
    permission_status = models.CharField(
        max_length=20, choices=PermissionStatus.choices, default=PermissionStatus.PENDING_REVIEW
    )
    terms_notes = models.TextField(
        blank=True,
        help_text="Notes on terms of use / partnership agreement covering this source. "
        "Attach or link the agreement where possible.",
    )
    contact_email = models.EmailField(blank=True, help_text="Contact at the source for partnership/authorization matters.")

    is_active = models.BooleanField(default=False)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    next_sync_at = models.DateTimeField(null=True, blank=True)
    sync_frequency_minutes = models.PositiveIntegerField(
        null=True, blank=True, help_text="How often this source should be re-synced, in minutes."
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.get_source_type_display()})"

    def clean(self):
        # Enforce the product rule in code, not just docs: a source cannot
        # be flipped active unless it has been authorized, and manual
        # ingestion is exempt from that check (an admin typing in a listing
        # by hand needs no external authorization).
        if self.is_active and self.permission_status != self.PermissionStatus.AUTHORIZED:
            if self.ingestion_method != self.IngestionMethod.MANUAL_ENTRY:
                raise ValidationError(
                    "A source can only be activated once its permission_status is AUTHORIZED "
                    "(or ingestion_method is MANUAL_ENTRY)."
                )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
