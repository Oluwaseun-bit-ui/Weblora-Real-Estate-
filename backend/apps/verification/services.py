"""
Application-level operations for the verification workflow, kept out of
views/admin so both the admin dashboard and any future API can share them.
"""
from django.utils import timezone

from apps.agencies.models import Agency
from apps.core.models import log_action

from .models import VerificationCheck


def record_check(*, agency: Agency, actor, check_kwargs: dict) -> VerificationCheck:
    """
    Creates a VerificationCheck from provider-built kwargs (see
    VerificationProvider.build_manual_check_kwargs) and updates the
    agency's regulatory identity fields + audit log accordingly.
    """
    check = VerificationCheck(agency=agency, checked_by=actor, **check_kwargs)
    check.full_clean()
    check.save()

    if check.result == VerificationCheck.Result.PASS and check.registration_number:
        field_map = {
            "ESVARBON": "esvarbon_registration_number",
            "LASRERA": "lasrera_registration_number",
            "CAC": "cac_registration_number",
        }
        field = field_map.get(check.check_type)
        if field:
            setattr(agency, field, check.registration_number)
            agency.save(update_fields=[field, "updated_at"])

    log_action(
        actor=actor,
        action="verification_check.recorded",
        obj=check,
        new_value={"check_type": check.check_type, "result": check.result, "method": check.method},
        notes=check.notes,
    )
    return check


def recompute_contact_status(agency: Agency, *, channel: str, status: str, actor=None):
    """Updates Agency.phone_status/email_status/website_status and logs it."""
    field = {
        "phone": "phone_status",
        "email": "email_status",
        "website": "website_status",
    }[channel]
    previous = getattr(agency, field)
    setattr(agency, field, status)
    agency.save(update_fields=[field, "updated_at"])
    if previous != status:
        log_action(
            actor=actor,
            action="agency.contact_status_changed",
            obj=agency,
            previous_value={field: previous},
            new_value={field: status},
        )


def approve_agency(agency: Agency, *, actor, recheck_in_days: int = 180) -> bool:
    """
    Approves an agency to VERIFIED status. Refuses (returns False) if the
    product rule for sufficient verified contact info isn't met, rather
    than letting an admin silently grant a status the evidence doesn't
    support -- the admin UI surfaces this as a validation error.
    """
    if not agency.has_sufficient_contact_info:
        return False
    previous = agency.verification_status
    agency.verification_status = Agency.VerificationStatus.VERIFIED
    agency.verification_recheck_date = (timezone.now() + timezone.timedelta(days=recheck_in_days)).date()
    agency.save(update_fields=["verification_status", "verification_recheck_date", "updated_at"])
    log_action(
        actor=actor,
        action="agency.verification_status_changed",
        obj=agency,
        previous_value={"verification_status": previous},
        new_value={"verification_status": agency.verification_status},
    )
    return True


def reject_agency(agency: Agency, *, actor, notes: str = ""):
    previous = agency.verification_status
    agency.verification_status = Agency.VerificationStatus.REJECTED
    agency.save(update_fields=["verification_status", "updated_at"])
    log_action(
        actor=actor,
        action="agency.verification_status_changed",
        obj=agency,
        previous_value={"verification_status": previous},
        new_value={"verification_status": agency.verification_status},
        notes=notes,
    )
