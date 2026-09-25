from django.utils import timezone

from .base import VerificationProvider, VerificationResult


class ContactVerificationProvider(VerificationProvider):
    """
    Verifies an agency's phone number and email actually work and belong to
    them. For the MVP this is a recorded workflow (e.g. an OTP call/SMS or a
    confirmation email sent and a reply received, or a verification officer
    placing a call) rather than a fully automated integration -- automating
    OTP delivery requires an SMS/email provider contract that is out of
    scope for Phase 1/2, but the interface is ready for one to be plugged
    in later (`is_automated` can flip to True once an OTP provider is
    wired up in `run_automated_check`).
    """

    check_type = "CONTACT_PHONE"  # overridden per-call via `for_channel`
    is_automated = False
    display_name = "Contact verification"

    def official_source_url(self) -> str:
        return "internal:contact-verification-workflow"

    @classmethod
    def for_channel(cls, channel: str) -> "ContactVerificationProvider":
        """channel: 'phone' or 'email'."""
        provider = cls()
        provider.check_type = "CONTACT_PHONE" if channel == "phone" else "CONTACT_EMAIL"
        provider.display_name = f"Contact verification ({channel})"
        return provider

    def manual_instructions(self) -> str:
        return (
            "Contact the agency through the number/email on file (call, SMS "
            "OTP, or a confirmation email requiring a reply) and confirm it "
            "reaches them. Record PROVIDED / VERIFIED / FAILED on the Agency "
            "record and log the check here with evidence (call notes, OTP "
            "confirmation reference, or the reply email)."
        )

    def record_result(self, *, passed: bool, notes: str = "") -> VerificationResult:
        return VerificationResult(
            result="PASS" if passed else "FAIL",
            evidence_reference=notes,
            source_url=self.official_source_url(),
            notes=notes,
        )
