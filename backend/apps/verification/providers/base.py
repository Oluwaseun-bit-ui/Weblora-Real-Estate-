"""
VerificationProvider abstraction.

Design goal (per product spec): the verification system is NOT hard-coded
around one regulator. Each regulator/check type is a provider that knows
how to produce (or help a human produce) a VerificationCheck. A provider
may be:

  - "manual"    -- there is no confirmed public API, so the provider exposes
                   a `manual_check_url()` (where a human goes to check) and a
                   `build_check(...)` helper that packages up what a human
                   found into a VerificationCheck with the correct `method`.
  - "automated" -- a real, permitted, documented API exists. Only flip a
                   provider to automated once that API is actually
                   integrated and confirmed; never assume one exists.

Providers never bypass CAPTCHA, auth walls, rate limits or anti-bot
controls, and never call an undocumented/unofficial endpoint. If a
provider cannot automate a check, `is_automated` MUST be False and the
provider MUST route through the manual workflow.
"""
from __future__ import annotations

import dataclasses
from typing import Optional

from django.utils import timezone


@dataclasses.dataclass
class VerificationResult:
    """What a provider hands back after a check (automated or manual)."""

    result: str  # VerificationCheck.Result value
    registration_number: str = ""
    subject_name: str = ""
    status_on_registry: str = ""
    evidence_reference: str = ""
    source_url: str = ""
    notes: str = ""
    checked_at = None


class VerificationProvider:
    """Base class every regulatory/contact/website provider implements."""

    #: VerificationCheck.CheckType value this provider produces checks for.
    check_type: str = ""

    #: Whether this provider currently performs the check automatically via
    #: an official, permitted API. Must stay False until a real integration
    #: is wired up and confirmed authorized.
    is_automated: bool = False

    #: Human-readable name shown in the admin verification queue.
    display_name: str = ""

    def official_source_url(self) -> str:
        """The official page/registry a human (or, later, an API) checks against."""
        raise NotImplementedError

    def manual_instructions(self) -> str:
        """Short instructions shown to the verification officer in the admin queue."""
        return f"Check {self.display_name} at {self.official_source_url()} and record the result."

    def run_automated_check(self, *, registration_number: str, subject_name: str) -> Optional[VerificationResult]:
        """
        Only implemented by providers where `is_automated` is True. Base
        implementation refuses to run, so a provider can never silently
        fall back to pretending it automated a check it didn't.
        """
        if not self.is_automated:
            raise NotImplementedError(
                f"{self.__class__.__name__} has no automated integration. "
                "Use the manual verification workflow instead."
            )
        raise NotImplementedError("Automated check not implemented.")

    def build_manual_check_kwargs(
        self,
        *,
        registration_number: str = "",
        subject_name: str = "",
        result: str,
        evidence_reference: str = "",
        notes: str = "",
        status_on_registry: str = "",
    ) -> dict:
        """
        Packages a human-recorded finding into the kwargs needed to create a
        VerificationCheck with method=MANUAL_PORTAL_CHECK, so callers (the
        admin verification queue view) don't have to know the mapping.
        """
        return dict(
            check_type=self.check_type,
            method="MANUAL_PORTAL_CHECK",
            source=self.official_source_url(),
            result=result,
            registration_number=registration_number,
            subject_name=subject_name,
            evidence_reference=evidence_reference,
            notes=notes,
            checked_at=timezone.now(),
        )
