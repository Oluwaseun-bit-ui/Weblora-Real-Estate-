import pytest
from django.core.exceptions import PermissionDenied

from apps.core.factories import AgencyFactory, PropertyFactory
from apps.live_viewing import services
from apps.live_viewing.models import AgencyRepresentative, LiveViewingRequest

pytestmark = pytest.mark.django_db


class TestLiveViewingLifecycle:
    def test_request_fails_when_live_viewing_not_available(self):
        prop = PropertyFactory(live_viewing_available=False)
        with pytest.raises(ValueError):
            services.request_live_viewing(
                property_obj=prop,
                customer_name="John",
                customer_email="john@example.com",
                customer_phone="",
                requested_date="2026-10-01",
                requested_time=None,
            )

    def test_full_accept_and_join_flow(self):
        agency = AgencyFactory()
        prop = PropertyFactory(agency=agency, live_viewing_available=True)
        viewing_request = services.request_live_viewing(
            property_obj=prop,
            customer_name="John",
            customer_email="john@example.com",
            customer_phone="",
            requested_date="2026-10-01",
            requested_time=None,
            message="Show me the kitchen",
        )
        assert viewing_request.status == LiveViewingRequest.Status.PENDING_AGENT

        rep = AgencyRepresentative.objects.create(agency=agency, name="Ada", phone_number="+2348010000001")
        session = services.accept_request(viewing_request, representative=rep)
        viewing_request.refresh_from_db()
        assert viewing_request.status == LiveViewingRequest.Status.SCHEDULED
        assert session.status == "SCHEDULED"

    def test_customer_cannot_join_with_wrong_token(self):
        agency = AgencyFactory()
        prop = PropertyFactory(agency=agency, live_viewing_available=True)
        viewing_request = services.request_live_viewing(
            property_obj=prop,
            customer_name="John",
            customer_email="john@example.com",
            customer_phone="",
            requested_date="2026-10-01",
            requested_time=None,
        )
        rep = AgencyRepresentative.objects.create(agency=agency, name="Ada")
        services.accept_request(viewing_request, representative=rep)

        with pytest.raises(PermissionDenied):
            services.join_as_customer(viewing_request, access_token="not-the-real-token")

    def test_representative_from_another_agency_cannot_join(self):
        agency = AgencyFactory()
        other_agency = AgencyFactory()
        prop = PropertyFactory(agency=agency, live_viewing_available=True)
        viewing_request = services.request_live_viewing(
            property_obj=prop,
            customer_name="John",
            customer_email="john@example.com",
            customer_phone="",
            requested_date="2026-10-01",
            requested_time=None,
        )
        rep = AgencyRepresentative.objects.create(agency=agency, name="Ada")
        services.accept_request(viewing_request, representative=rep)

        intruder = AgencyRepresentative.objects.create(agency=other_agency, name="Bad Actor")
        with pytest.raises(PermissionDenied):
            services.join_as_representative(viewing_request, representative=intruder)

    def test_no_video_provider_configured_raises_not_pretends_to_work(self):
        # settings.LIVE_VIEWING_PROVIDER defaults to "none" in tests unless overridden
        agency = AgencyFactory()
        prop = PropertyFactory(agency=agency, live_viewing_available=True)
        viewing_request = services.request_live_viewing(
            property_obj=prop,
            customer_name="John",
            customer_email="john@example.com",
            customer_phone="",
            requested_date="2026-10-01",
            requested_time=None,
        )
        rep = AgencyRepresentative.objects.create(agency=agency, name="Ada")
        services.accept_request(viewing_request, representative=rep)
        with pytest.raises(NotImplementedError):
            services.join_as_customer(viewing_request, access_token=viewing_request.customer_access_token)
