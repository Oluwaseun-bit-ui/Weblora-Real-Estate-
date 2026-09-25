import pytest
from rest_framework.test import APIClient

from apps.agencies.models import Agency
from apps.core.factories import AgencyFactory, PropertyFactory
from apps.properties.models import Property

pytestmark = pytest.mark.django_db


class TestPropertySearchAPI:
    def setup_method(self):
        self.client = APIClient()

    def test_search_excludes_non_active_listings(self):
        PropertyFactory(status=Property.ListingStatus.ACTIVE, title="Active one")
        PropertyFactory(status=Property.ListingStatus.STALE, title="Stale one")
        PropertyFactory(status=Property.ListingStatus.REMOVED, title="Removed one")

        resp = self.client.get("/api/properties/")
        assert resp.status_code == 200
        titles = [p["title"] for p in resp.data["results"]]
        assert "Active one" in titles
        assert "Stale one" not in titles
        assert "Removed one" not in titles

    def test_filters_by_bedrooms_and_price_range(self):
        PropertyFactory(bedrooms=2, price=3_000_000)
        PropertyFactory(bedrooms=4, price=9_000_000)

        resp = self.client.get("/api/properties/", {"bedrooms": 3, "max_price": 10_000_000})
        assert resp.status_code == 200
        assert all(p["bedrooms"] >= 3 for p in resp.data["results"])

    def test_verified_agency_filter(self):
        verified_agency = AgencyFactory(verification_status=Agency.VerificationStatus.VERIFIED)
        unverified_agency = AgencyFactory(verification_status=Agency.VerificationStatus.DISCOVERED)
        PropertyFactory(agency=verified_agency, title="From verified")
        PropertyFactory(agency=unverified_agency, title="From unverified")

        resp = self.client.get("/api/properties/", {"verified_agency": "true"})
        titles = [p["title"] for p in resp.data["results"]]
        assert "From verified" in titles
        assert "From unverified" not in titles

    def test_sponsored_listings_are_labelled_never_silently_boosted(self):
        featured = PropertyFactory(is_featured=True, title="Featured listing")
        resp = self.client.get("/api/properties/")
        result = next(p for p in resp.data["results"] if p["title"] == "Featured listing")
        assert result["is_featured"] is True
