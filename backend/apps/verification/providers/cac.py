from django.conf import settings

from .base import VerificationProvider


class CACProvider(VerificationProvider):
    """
    Corporate Affairs Commission (business registration) verification.

    Manual workflow only: CAC's public search is used by a human to
    confirm a company/business name and registration number; the finding
    is recorded as evidence. Do not claim CAC verification unless this
    workflow (or a future authorized API) was actually used.
    """

    check_type = "CAC"
    is_automated = False
    display_name = "CAC"

    def official_source_url(self) -> str:
        return settings.CAC_PUBLIC_SEARCH_URL

    def manual_instructions(self) -> str:
        return (
            f"Search the CAC public portal ({self.official_source_url()}) for the "
            "agency's registered business name/RC number. Record the registration "
            "status and number as evidence. Do not bypass CAPTCHA or rate limits."
        )
