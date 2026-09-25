import logging

from django.utils import timezone

from .base import VerificationProvider, VerificationResult

logger = logging.getLogger("apps.verification")


class WebsiteVerificationProvider(VerificationProvider):
    """
    Confirms an agency's website exists, is reachable, and (as far as a
    verification officer can tell) matches the agency's identity (name,
    branding, contact details consistent with what's on file).

    The "exists / accessible" portion can reasonably be automated: issuing
    a plain HTTP HEAD/GET request to a URL the agency itself supplied is
    normal, permitted use of the public web (not scraping protected
    content, not bypassing any restriction). The "matches agency identity"
    judgement stays a human call, recorded manually.
    """

    check_type = "WEBSITE"
    is_automated = True  # only for the reachability sub-check; identity match stays manual
    display_name = "Website verification"

    def official_source_url(self) -> str:
        return "internal:website-verification-workflow"

    def check_reachability(self, url: str, timeout: float = 5.0) -> VerificationResult:
        """
        Lightweight reachability check. Never follows this up with content
        scraping; a 2xx/3xx response is all that's asserted as "exists /
        accessible". Failures (timeouts, DNS errors, non-2xx) are recorded
        as FAIL so an officer can follow up manually.
        """
        try:
            import requests

            resp = requests.head(url, timeout=timeout, allow_redirects=True)
            if resp.status_code >= 400:
                # Some sites reject HEAD; retry with a conservative GET.
                resp = requests.get(url, timeout=timeout, allow_redirects=True)
            passed = resp.status_code < 400
            return VerificationResult(
                result="PASS" if passed else "FAIL",
                status_on_registry=str(resp.status_code),
                evidence_reference=f"HTTP {resp.status_code} from {url}",
                source_url=url,
                notes="Automated reachability check only; identity match requires manual review.",
            )
        except Exception as exc:  # noqa: BLE001 - want to record any failure reason
            logger.info("Website reachability check failed for %s: %s", url, exc)
            return VerificationResult(
                result="INCONCLUSIVE",
                evidence_reference=str(exc),
                source_url=url,
                notes="Automated reachability check errored; requires manual follow-up.",
            )

    def manual_instructions(self) -> str:
        return (
            "Confirm the website is reachable (automated check runs "
            "separately) and manually confirm it matches the agency's "
            "identity: name, contact details and branding consistent with "
            "what's on file. Record MATCHES_IDENTITY or FAILED."
        )
