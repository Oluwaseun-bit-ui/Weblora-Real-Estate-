import pytest

from apps.agencies.models import Agency
from apps.core.factories import AgencyFactory
from apps.verification import services as verification_services
from apps.verification.models import VerificationCheck

pytestmark = pytest.mark.django_db


class TestAgencyVerificationRules:
    def test_new_agency_defaults_to_discovered_and_no_badges(self):
        agency = AgencyFactory()
        assert agency.verification_status == Agency.VerificationStatus.DISCOVERED
        assert agency.verification_badges() == []

    def test_cannot_approve_without_sufficient_contact_info(self):
        agency = AgencyFactory()
        assert agency.has_sufficient_contact_info is False
        approved = verification_services.approve_agency(agency, actor=None)
        assert approved is False
        agency.refresh_from_db()
        assert agency.verification_status != Agency.VerificationStatus.VERIFIED

    def test_approve_succeeds_once_contact_info_verified(self):
        agency = AgencyFactory()
        agency.phone_status = Agency.ContactFieldStatus.VERIFIED
        agency.email_status = Agency.ContactFieldStatus.VERIFIED
        agency.save()
        approved = verification_services.approve_agency(agency, actor=None)
        assert approved is True
        agency.refresh_from_db()
        assert agency.verification_status == Agency.VerificationStatus.VERIFIED
        assert agency.verification_recheck_date is not None

    def test_esvarbon_badge_requires_a_recorded_pass_check_not_just_a_number(self):
        agency = AgencyFactory(esvarbon_registration_number="ESV/12345")
        assert "ESVARBON Verified" not in agency.verification_badges()

        VerificationCheck.objects.create(
            agency=agency,
            check_type=VerificationCheck.CheckType.ESVARBON,
            method=VerificationCheck.Method.MANUAL_PORTAL_CHECK,
            source="https://portal.esvarbon.gov.ng/pages/verify",
            result=VerificationCheck.Result.PASS,
            registration_number="ESV/12345",
            checked_at="2026-01-01T00:00:00Z",
        )
        assert "ESVARBON Verified" in agency.verification_badges()

    def test_verification_check_rejects_automated_method_for_esvarbon(self):
        agency = AgencyFactory()
        check = VerificationCheck(
            agency=agency,
            check_type=VerificationCheck.CheckType.ESVARBON,
            method=VerificationCheck.Method.AUTOMATED_API,
            source="https://portal.esvarbon.gov.ng/pages/verify",
            result=VerificationCheck.Result.PASS,
            checked_at="2026-01-01T00:00:00Z",
        )
        with pytest.raises(Exception):
            check.full_clean()
