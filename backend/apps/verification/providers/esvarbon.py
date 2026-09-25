from django.conf import settings

from .base import VerificationProvider


class ESVARBONProvider(VerificationProvider):
    """
    ESVARBON (Estate Surveyors and Valuers Registration Board of Nigeria)
    verification for practitioners and firms.

    As of this build, ESVARBON does not publish a documented public API --
    only a web portal for humans to check a registration number/name
    against the register. So `is_automated` stays False and every check
    goes through the manual workflow: a verification officer visits the
    official portal, looks up the practitioner/firm, and records what they
    found (with evidence) via `build_manual_check_kwargs`.

    If ESVARBON ever publishes an official API, only this class needs to
    change (implement `run_automated_check` and flip `is_automated = True`)
    -- nothing else in the application depends on how the check is
    performed.
    """

    check_type = "ESVARBON"
    is_automated = False
    display_name = "ESVARBON"

    def official_source_url(self) -> str:
        return settings.ESVARBON_VERIFY_URL

    def register_url(self) -> str:
        return settings.ESVARBON_REGISTER_URL

    def manual_instructions(self) -> str:
        return (
            "Go to the official ESVARBON verification portal "
            f"({self.official_source_url()}) and/or the published register "
            f"({self.register_url()}). Look up the practitioner/firm by "
            "registration number or name. Record: registration status, "
            "registration number, name as shown, and a screenshot or "
            "reference as evidence. Do not attempt to bypass any login, "
            "CAPTCHA or rate limit on the portal."
        )
