from decimal import Decimal

import pytest

from apps.agencies.models import Agency
from apps.core.factories import PropertySourceFactory
from apps.properties.models import PriceHistory, Property
from apps.sources.ingestion.base import SourceAdapter
from apps.sources.ingestion.propertyspot import parse_agent, parse_listing
from apps.sources.models import PropertySource
from apps.sources.services import sync_source

pytestmark = pytest.mark.django_db

PROPERTYSPOT_ITEM = {
    "id": 1914,
    "address": "Lekki phase 1 lagos",
    "title": "NEWLY BUILT 4-BEDROOM SERVICED APARTMENTS WITH BQ",
    "purpose": "rent",
    "is_land": 0,
    "description": "Fully furnished apartment",
    "price": "25,000,000.00",
    "price_duration": "year",
    "status": "available",
    "image": "https://img.example/main.jpg",
    "bedrooms": 4,
    "bathrooms": 4,
    "location": {"id": 773, "name": "Lekki", "state": {"id": 24, "name": "Lagos"}},
    "images": [{"id": 1, "image": "https://img.example/1.jpg"}, {"id": 2, "image": "https://img.example/main.jpg"}],
    "amenities_by_category": [{"category": {"name": "Basic"}, "amenities": [{"name": "Electricity"}, {"name": "BQ "}]}],
}

PROPERTYSPOT_AGENT = {
    "id": 285,
    "first_name": "fortune",
    "last_name": "kennzee",
    "company_name": None,
    "email": "agent@example.com",
    "phone_number": "08038572219",
    "address": "ocean palm estate, Lagos",
    "nin": "12345678901",
    "bvn": "22222222222",
    "id_card_image": "https://example/id.jpg",
}


class TestPropertySpotParsing:
    def test_parse_listing_maps_fields(self):
        rec = parse_listing(PROPERTYSPOT_ITEM, "rent")
        assert rec.external_id == "1914"
        assert rec.price == Decimal("25000000.00")
        assert rec.transaction_type == "RENT"
        assert rec.property_type == "APARTMENT"
        assert rec.price_period == "year"
        assert rec.furnished_status == "FURNISHED"
        assert rec.state == "Lagos" and rec.area == "Lekki"
        assert rec.amenities == ["Electricity", "BQ"]
        assert rec.image_urls == ["https://img.example/main.jpg", "https://img.example/1.jpg"]
        assert rec.source_url.endswith("single-property.html?id=1914")

    def test_land_and_sale_mapping(self):
        rec = parse_listing({**PROPERTYSPOT_ITEM, "is_land": "1", "title": "Plot in Ibeju"}, "sale")
        assert rec.property_type == "LAND"
        assert rec.transaction_type == "BUY"

    def test_parse_agent_keeps_contacts_and_drops_id_numbers(self):
        agency = parse_agent(PROPERTYSPOT_AGENT)
        assert agency.name == "Fortune Kennzee"
        assert agency.phone_number == "+2348038572219"
        assert agency.whatsapp_number == "2348038572219"
        dumped = str(vars(agency))
        assert "12345678901" not in dumped and "22222222222" not in dumped and "id.jpg" not in dumped


class FakeAdapter(SourceAdapter):
    def __init__(self, source, listings, agent=PROPERTYSPOT_AGENT):
        super().__init__(source)
        self.listings = listings
        self.agent = agent
        self.agency_calls = 0

    def iter_listings(self):
        yield from self.listings

    def fetch_agency(self, listing):
        self.agency_calls += 1
        return parse_agent(self.agent)


def _source():
    return PropertySourceFactory(
        adapter="propertyspot",
        source_type=PropertySource.SourceType.LISTING_PARTNER_FEED,
        ingestion_method=PropertySource.IngestionMethod.PARTNER_FEED,
    )


class TestSyncSource:
    def test_first_sync_creates_listing_agency_and_images(self):
        source = _source()
        result = sync_source(source, FakeAdapter(source, [parse_listing(PROPERTYSPOT_ITEM, "rent")]))

        assert (result.created, result.agencies_created) == (1, 1)
        prop = Property.objects.get(source=source, source_property_id="1914")
        assert prop.status == Property.ListingStatus.ACTIVE
        assert prop.agency.phone_number == "+2348038572219"
        assert prop.agency.phone_status == Agency.ContactFieldStatus.PROVIDED
        assert prop.images.filter(display_authorized=True).count() == 2
        source.refresh_from_db()
        assert source.last_synced_at and source.next_sync_at

    def test_resync_updates_without_duplicates_and_records_price_change(self):
        source = _source()
        sync_source(source, FakeAdapter(source, [parse_listing(PROPERTYSPOT_ITEM, "rent")]))
        adapter = FakeAdapter(source, [parse_listing({**PROPERTYSPOT_ITEM, "price": "27,000,000"}, "rent")])
        result = sync_source(source, adapter)

        assert (result.created, result.updated) == (0, 1)
        assert adapter.agency_calls == 0  # agency already known, no extra detail request
        assert Property.objects.filter(source=source).count() == 1
        assert Agency.objects.filter(source_agency_id="285").count() == 1
        assert PriceHistory.objects.get().price == Decimal("25000000.00")

    def test_listing_missing_from_source_is_marked_stale(self):
        source = _source()
        sync_source(source, FakeAdapter(source, [parse_listing(PROPERTYSPOT_ITEM, "rent")]))
        result = sync_source(source, FakeAdapter(source, []))

        assert result.marked_stale == 1
        assert Property.objects.get().status == Property.ListingStatus.STALE

    def test_verified_agency_is_not_overwritten(self):
        source = _source()
        sync_source(source, FakeAdapter(source, [parse_listing(PROPERTYSPOT_ITEM, "rent")]))
        Agency.objects.update(verification_status=Agency.VerificationStatus.VERIFIED, phone_number="+2340000000000")
        Property.objects.update(agency=None)  # force the agency to be looked up again
        sync_source(source, FakeAdapter(source, [parse_listing(PROPERTYSPOT_ITEM, "rent")]))

        assert Agency.objects.get().phone_number == "+2340000000000"

    def test_unauthorized_source_is_refused(self):
        source = _source()
        PropertySource.objects.filter(pk=source.pk).update(permission_status=PropertySource.PermissionStatus.REVOKED)
        source.refresh_from_db()
        with pytest.raises(ValueError):
            sync_source(source, FakeAdapter(source, []))
