from django.conf import settings
from django.db import models

from apps.agencies.models import Agency
from apps.core.models import TimeStampedModel


class VerificationCheck(TimeStampedModel):
    """
    A single recorded verification check against an agency (or, in future,
    a practitioner). This is the system of record for "what did we actually
    check, and what did we find" -- the Agency.verification_status and
    badges are derived from these records, never asserted independently.
    """

    class CheckType(models.TextChoices):
        ESVARBON = "ESVARBON", "ESVARBON (Estate Surveyors & Valuers)"
        LASRERA = "LASRERA", "LASRERA (Lagos State Real Estate Regulatory Authority)"
        CAC = "CAC", "CAC (Corporate Affairs Commission)"
        CONTACT_PHONE = "CONTACT_PHONE", "Contact — phone"
        CONTACT_EMAIL = "CONTACT_EMAIL", "Contact — email"
        WEBSITE = "WEBSITE", "Website"
        MANUAL_REVIEW = "MANUAL_REVIEW", "General manual review"

    class Result(models.TextChoices):
        PASS = "PASS", "Pass"
        FAIL = "FAIL", "Fail"
        INCONCLUSIVE = "INCONCLUSIVE", "Inconclusive"
        NOT_APPLICABLE = "NOT_APPLICABLE", "Not applicable"

    class Method(models.TextChoices):
        # A verification check is either done through an *actual* automated
        # API/integration, or it is a human checking an official source and
        # recording the result. The system must never let a manual result
        # be mislabeled as an automated API verification.
        AUTOMATED_API = "AUTOMATED_API", "Automated API integration"
        MANUAL_PORTAL_CHECK = "MANUAL_PORTAL_CHECK", "Manual check of an official portal/registry"
        MANUAL_CONTACT = "MANUAL_CONTACT", "Manual contact (call/email) with agency or regulator"
        DOCUMENT_REVIEW = "DOCUMENT_REVIEW", "Document review"

    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name="verification_checks")

    check_type = models.CharField(max_length=20, choices=CheckType.choices)
    method = models.CharField(max_length=24, choices=Method.choices)
    source = models.CharField(
        max_length=255,
        help_text="Where the check was performed, e.g. 'https://portal.esvarbon.gov.ng/pages/verify' or 'Phone call to agency'.",
    )
    result = models.CharField(max_length=16, choices=Result.choices)

    registration_number = models.CharField(max_length=64, blank=True, help_text="Registration/licence number checked, if applicable.")
    subject_name = models.CharField(max_length=255, blank=True, help_text="Practitioner/firm name as checked against the registry.")

    evidence_reference = models.TextField(
        blank=True,
        help_text="Reference/evidence supporting the result: screenshot filename, reference number, saved copy link, etc.",
    )
    evidence_file = models.FileField(upload_to="verification_evidence/", blank=True, null=True)

    notes = models.TextField(blank=True)

    checked_at = models.DateTimeField(help_text="When the check was actually performed (may differ from created_at).")
    checked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="verification_checks_performed"
    )

    expiration_date = models.DateField(null=True, blank=True, help_text="When this check's result should be treated as stale.")
    recheck_date = models.DateField(null=True, blank=True, help_text="When this check should next be performed.")

    class Meta:
        ordering = ["-checked_at"]
        indexes = [
            models.Index(fields=["agency", "check_type"]),
            models.Index(fields=["result"]),
        ]

    def __str__(self):
        return f"{self.get_check_type_display()} — {self.agency.name} — {self.result}"

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.method == self.Method.AUTOMATED_API and self.check_type in {
            self.CheckType.ESVARBON,
            self.CheckType.LASRERA,
        }:
            # Neither regulator currently exposes a confirmed public API.
            # Guard against ever silently mislabeling a manual check.
            raise ValidationError(
                f"{self.check_type} has no confirmed automated API as of this build. "
                "Record this check as MANUAL_PORTAL_CHECK, MANUAL_CONTACT or DOCUMENT_REVIEW instead."
            )


class RegulatoryRecord(TimeStampedModel):
    """
    A cached/stored snapshot of what a regulator's public registry showed
    for an agency/practitioner at a point in time, tied to the
    VerificationCheck that produced it. Kept separate from VerificationCheck
    so multiple checks can reference the same underlying registry record
    over time (e.g. rechecking the same registration number every 6 months).
    """

    class Regulator(models.TextChoices):
        ESVARBON = "ESVARBON", "ESVARBON"
        LASRERA = "LASRERA", "LASRERA"
        CAC = "CAC", "CAC"

    regulator = models.CharField(max_length=16, choices=Regulator.choices)
    registration_number = models.CharField(max_length=64)
    subject_name = models.CharField(max_length=255, blank=True)
    status_on_registry = models.CharField(max_length=100, blank=True, help_text="Status as shown on the official registry, verbatim where possible.")
    raw_reference = models.TextField(blank=True, help_text="Verbatim notes/reference captured from the official source.")
    source_url = models.URLField(blank=True)
    checked_at = models.DateTimeField()

    verification_check = models.ForeignKey(
        VerificationCheck, on_delete=models.CASCADE, related_name="regulatory_records", null=True, blank=True
    )

    class Meta:
        ordering = ["-checked_at"]
        indexes = [models.Index(fields=["regulator", "registration_number"])]

    def __str__(self):
        return f"{self.regulator} #{self.registration_number}"
