from django.db import models
from django.utils.text import slugify

from apps.core.models import TimeStampedModel
from apps.sources.models import PropertySource


class Agency(TimeStampedModel):
    """
    A real-estate agency/agency-individual practitioner discovered or
    manually entered on the platform. Agencies do NOT register themselves
    for the MVP -- this record is created by ingestion or by an admin, and
    its verification status is earned through the VerificationCheck
    workflow, never assumed.
    """

    class VerificationStatus(models.TextChoices):
        DISCOVERED = "DISCOVERED", "Discovered"
        PENDING_REVIEW = "PENDING_REVIEW", "Pending review"
        VERIFICATION_IN_PROGRESS = "VERIFICATION_IN_PROGRESS", "Verification in progress"
        VERIFIED = "VERIFIED", "Verified"
        REJECTED = "REJECTED", "Rejected"
        SUSPENDED = "SUSPENDED", "Suspended"
        EXPIRED_RECHECK_REQUIRED = "EXPIRED_RECHECK_REQUIRED", "Expired / recheck required"

    class ContactFieldStatus(models.TextChoices):
        NOT_PROVIDED = "NOT_PROVIDED", "Not provided"
        PROVIDED = "PROVIDED", "Provided"
        VERIFIED = "VERIFIED", "Verified"
        FAILED = "FAILED", "Failed"

    class WebsiteStatus(models.TextChoices):
        NOT_PROVIDED = "NOT_PROVIDED", "Not provided"
        EXISTS = "EXISTS", "Exists"
        ACCESSIBLE = "ACCESSIBLE", "Accessible"
        MATCHES_IDENTITY = "MATCHES_IDENTITY", "Matches agency identity"
        FAILED = "FAILED", "Failed"

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, unique=True, blank=True)
    description = models.TextField(blank=True)

    logo = models.ImageField(upload_to="agency_logos/", blank=True, null=True)
    logo_display_authorized = models.BooleanField(
        default=False, help_text="Only show the logo publicly once we have permission to display it."
    )

    website = models.URLField(blank=True)
    phone_number = models.CharField(max_length=32, blank=True)
    email = models.EmailField(blank=True)
    whatsapp_number = models.CharField(max_length=32, blank=True)

    business_address = models.CharField(max_length=500, blank=True)
    service_locations = models.JSONField(default=list, blank=True, help_text="List of area/city names served.")

    # --- Regulatory identity (populated by VerificationCheck evidence, not
    # free-typed claims) ---
    cac_registration_number = models.CharField(max_length=64, blank=True)
    esvarbon_registration_number = models.CharField(max_length=64, blank=True)
    lasrera_registration_number = models.CharField(max_length=64, blank=True)

    verification_status = models.CharField(
        max_length=32, choices=VerificationStatus.choices, default=VerificationStatus.DISCOVERED
    )
    verification_recheck_date = models.DateField(null=True, blank=True)

    phone_status = models.CharField(max_length=16, choices=ContactFieldStatus.choices, default=ContactFieldStatus.NOT_PROVIDED)
    email_status = models.CharField(max_length=16, choices=ContactFieldStatus.choices, default=ContactFieldStatus.NOT_PROVIDED)
    website_status = models.CharField(max_length=20, choices=WebsiteStatus.choices, default=WebsiteStatus.NOT_PROVIDED)

    sources = models.ManyToManyField(PropertySource, related_name="agencies", blank=True)
    source_agency_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="The agency's/agent's ID on the source it was ingested from, used to avoid duplicates on re-sync.",
    )

    is_suspended = models.BooleanField(default=False)
    suspension_reason = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "agencies"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["verification_status"]),
            models.Index(fields=["slug"]),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)[:250]
            slug = base_slug
            i = 1
            while Agency.objects.exclude(pk=self.pk).filter(slug=slug).exists():
                i += 1
                slug = f"{base_slug}-{i}"
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def has_sufficient_contact_info(self) -> bool:
        """
        Product rule: an agency cannot be marked VERIFIED without enough
        verified contact information. "Sufficient" here requires at least
        one verified channel (phone or email) plus a verified/matching
        website OR a second verified channel.
        """
        verified_channels = sum(
            [
                self.phone_status == self.ContactFieldStatus.VERIFIED,
                self.email_status == self.ContactFieldStatus.VERIFIED,
            ]
        )
        website_ok = self.website_status in {self.WebsiteStatus.ACCESSIBLE, self.WebsiteStatus.MATCHES_IDENTITY}
        return verified_channels >= 2 or (verified_channels >= 1 and website_ok)

    def verification_badges(self):
        """
        Returns a list of explicit, evidence-backed badges for display.
        Never returns a generic "100% trusted" style claim -- each badge
        names exactly what was checked.
        """
        badges = []
        if self.esvarbon_registration_number and self.verification_checks.filter(
            check_type="ESVARBON", result="PASS"
        ).exists():
            badges.append("ESVARBON Verified")
        if self.lasrera_registration_number and self.verification_checks.filter(
            check_type="LASRERA", result="PASS"
        ).exists():
            badges.append("LASRERA Verified")
        if self.cac_registration_number and self.verification_checks.filter(check_type="CAC", result="PASS").exists():
            badges.append("CAC Verified")
        if self.phone_status == self.ContactFieldStatus.VERIFIED or self.email_status == self.ContactFieldStatus.VERIFIED:
            badges.append("Contact Verified")
        if self.website_status in {self.WebsiteStatus.ACCESSIBLE, self.WebsiteStatus.MATCHES_IDENTITY}:
            badges.append("Website Verified")
        return badges
