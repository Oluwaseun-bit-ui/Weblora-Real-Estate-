from django.conf import settings

from .base import VerificationProvider


class LASRERAProvider(VerificationProvider):
    """
    Lagos State Real Estate Regulatory Authority verification.

    No official LASRERA API or confirmed automated public verification
    mechanism is assumed. This provider is manual-only: an admin records a
    LASRERA registration/licence number, agency/practitioner name, status,
    official source/reference, date checked, evidence, reviewer and notes.

    Replaceable design: if LASRERA later ships an official API or public
    verification mechanism, implement `run_automated_check` here and flip
    `is_automated = True`. No other app code needs to change -- the admin
    verification queue and Agency model only depend on this provider's
    interface, not on how the check happens.
    """

    check_type = "LASRERA"
    is_automated = False
    display_name = "LASRERA"

    def official_source_url(self) -> str:
        return settings.LASRERA_INFO_URL

    def manual_instructions(self) -> str:
        return (
            "No confirmed official LASRERA online verification mechanism is "
            "wired up. Verify the agency/practitioner's LASRERA registration "
            "through LASRERA's official channels (their website/office) and "
            "record: registration/licence number, agency/practitioner name, "
            "status, official source/reference, evidence, and a recheck date."
        )
