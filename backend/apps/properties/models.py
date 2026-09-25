from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.db import models

from apps.agencies.models import Agency
from apps.core.models import TimeStampedModel
from apps.sources.models import PropertySource


class Property(TimeStampedModel):
    class PropertyType(models.TextChoices):
        APARTMENT = "APARTMENT", "Apartment"
        HOUSE = "HOUSE", "House"
        DUPLEX = "DUPLEX", "Duplex"
        BUNGALOW = "BUNGALOW", "Bungalow"
        TERRACE = "TERRACE", "Terrace"
        LAND = "LAND", "Land"
        SHORTLET = "SHORTLET", "Shortlet"
        COMMERCIAL = "COMMERCIAL", "Commercial"
        OTHER = "OTHER", "Other"

    class TransactionType(models.TextChoices):
        RENT = "RENT", "Rent"
        BUY = "BUY", "Buy"
        SHORTLET = "SHORTLET", "Shortlet"

    class FurnishedStatus(models.TextChoices):
        FURNISHED = "FURNISHED", "Furnished"
        SEMI_FURNISHED = "SEMI_FURNISHED", "Semi-furnished"
        UNFURNISHED = "UNFURNISHED", "Unfurnished"
        UNKNOWN = "UNKNOWN", "Unknown"

    class ListingStatus(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        PENDING_REVIEW = "PENDING_REVIEW", "Pending review"
        STALE = "STALE", "Stale / needs recheck"
        REMOVED = "REMOVED", "Removed"

    class VerificationStatus(models.TextChoices):
        SOURCE_CONFIRMED = "SOURCE_CONFIRMED", "Source confirmed"
        AGENCY_PROVIDED = "AGENCY_PROVIDED", "Agency provided"
        INDEPENDENTLY_VERIFIED = "INDEPENDENTLY_VERIFIED", "Independently verified"
        PENDING_REVIEW = "PENDING_REVIEW", "Pending review"
        REMOVED = "REMOVED", "Removed"
        STALE = "STALE", "Stale"

    # --- Core listing info ---
    title = models.CharField(max_length=500)
    description = models.TextField(blank=True)
    property_type = models.CharField(max_length=20, choices=PropertyType.choices)
    transaction_type = models.CharField(max_length=20, choices=TransactionType.choices)

    price = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=8, default="NGN")
    price_period = models.CharField(
        max_length=20,
        blank=True,
        help_text="e.g. 'year', 'month', 'night' for rent/shortlet pricing.",
    )

    # --- Location ---
    location = models.CharField(max_length=255, help_text="Free-text area/neighbourhood, e.g. 'Lekki Phase 1'.")
    state = models.CharField(max_length=100, default="Lagos")
    city = models.CharField(max_length=120, blank=True)
    area = models.CharField(max_length=150, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    # --- Attributes ---
    bedrooms = models.PositiveSmallIntegerField(null=True, blank=True)
    bathrooms = models.PositiveSmallIntegerField(null=True, blank=True)
    toilets = models.PositiveSmallIntegerField(null=True, blank=True)
    amenities = models.JSONField(default=list, blank=True, help_text="List of amenity strings, e.g. ['pool', 'gym', '24/7 power'].")
    furnished_status = models.CharField(max_length=20, choices=FurnishedStatus.choices, default=FurnishedStatus.UNKNOWN)

    # --- Provenance ---
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name="properties", null=True, blank=True)
    source = models.ForeignKey(PropertySource, on_delete=models.SET_NULL, null=True, blank=True, related_name="properties")
    source_url = models.URLField(blank=True)
    source_property_id = models.CharField(max_length=255, blank=True, help_text="The property's ID/reference on the source system, if any.")

    # --- Lifecycle / freshness tracking ---
    status = models.CharField(max_length=20, choices=ListingStatus.choices, default=ListingStatus.PENDING_REVIEW)
    verification_status = models.CharField(max_length=30, choices=VerificationStatus.choices, default=VerificationStatus.AGENCY_PROVIDED)
    discovered_at = models.DateTimeField(auto_now_add=True)
    last_checked_at = models.DateTimeField(null=True, blank=True, help_text="Last time we actively re-confirmed this listing.")
    last_seen_at = models.DateTimeField(null=True, blank=True, help_text="Last time the source still showed this listing as available.")

    # Live viewing availability flag; the actual scheduling lives in
    # apps.live_viewing.LiveViewingRequest.
    live_viewing_available = models.BooleanField(default=False)

    # Sponsored/featured listings must be clearly labelled in the UI per
    # product rule (never silently boosted by payment).
    is_featured = models.BooleanField(default=False)

    search_vector = SearchVectorField(null=True, blank=True, editable=False)

    class Meta:
        verbose_name_plural = "properties"
        ordering = ["-discovered_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["verification_status"]),
            models.Index(fields=["property_type", "transaction_type"]),
            models.Index(fields=["state", "city", "area"]),
            models.Index(fields=["price"]),
            GinIndex(fields=["search_vector"]),
        ]

    def __str__(self):
        return f"{self.title} — {self.location}"

    @property
    def is_stale(self) -> bool:
        return self.status == self.ListingStatus.STALE

    def mark_seen(self, *, checked=True):
        """Called by ingestion sync when a listing is confirmed still present at the source."""
        from django.utils import timezone

        now = timezone.now()
        self.last_seen_at = now
        if checked:
            self.last_checked_at = now
        if self.status == self.ListingStatus.STALE:
            self.status = self.ListingStatus.ACTIVE
        self.save(update_fields=["last_seen_at", "last_checked_at", "status", "updated_at"])


class PriceHistory(TimeStampedModel):
    """Tracks price changes over time for stale-listing/analytics purposes."""

    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="price_history")
    price = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=8, default="NGN")
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-recorded_at"]
        verbose_name_plural = "price history"


class PropertyImage(TimeStampedModel):
    """
    Images are only attached where we have permission to display them
    (agency-provided media, or images from a source whose terms allow
    redisplay). Stored in external object storage via the configured
    Django storage backend, never inlined into Postgres.
    """

    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="property_images/", blank=True)
    external_url = models.URLField(
        max_length=1000,
        blank=True,
        help_text="Image hosted by the source (used for ingested listings instead of copying the file).",
    )
    display_authorized = models.BooleanField(
        default=False, help_text="Must be explicitly true before this image is served publicly."
    )
    caption = models.CharField(max_length=255, blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "created_at"]
