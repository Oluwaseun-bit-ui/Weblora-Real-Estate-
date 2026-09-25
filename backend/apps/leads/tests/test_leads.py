import pytest
from rest_framework.test import APIClient

from apps.core.factories import AgencyFactory, PropertyFactory
from apps.leads.models import Lead

pytestmark = pytest.mark.django_db


class TestLeadSubmission:
    def setup_method(self):
        self.client = APIClient()

    def test_submitting_a_lead_requires_consent(self):
        agency = AgencyFactory()
        prop = PropertyFactory(agency=agency)
        resp = self.client.post(
            "/api/leads/",
            {
                "property_id": str(prop.id),
                "agency": str(agency.id),
                "customer_name": "John",
                "customer_phone": "+2348010000000",
                "message": "Interested",
                "consent_given": False,
            },
        )
        assert resp.status_code == 400
        assert "consent_given" in resp.data

    def test_valid_lead_is_created_and_marked_sent(self):
        agency = AgencyFactory()
        prop = PropertyFactory(agency=agency)
        resp = self.client.post(
            "/api/leads/",
            {
                "property_id": str(prop.id),
                "agency": str(agency.id),
                "customer_name": "John",
                "customer_phone": "+2348010000000",
                "message": "Interested",
                "consent_given": True,
            },
        )
        assert resp.status_code == 201
        lead = Lead.objects.get(id=resp.data["id"])
        assert lead.status == Lead.Status.SENT
        assert lead.referred_at is not None

    def test_lead_requires_email_or_phone(self):
        agency = AgencyFactory()
        resp = self.client.post(
            "/api/leads/",
            {"agency": str(agency.id), "customer_name": "John", "consent_given": True},
        )
        assert resp.status_code == 400
