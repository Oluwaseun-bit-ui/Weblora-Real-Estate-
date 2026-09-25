"""
Adapter interface for ingesting listings from an authorized PropertySource.

An adapter only knows how to *read* one source and translate it into plain
records. Everything about how records land in our database (dedupe, price
history, stale marking, image permissions) lives in
apps.sources.services.sync_source, so adding a new source never touches
those rules.
"""
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Iterator, Optional


@dataclass
class AgencyRecord:
    external_id: str
    name: str
    phone_number: str = ""
    email: str = ""
    whatsapp_number: str = ""
    website: str = ""
    business_address: str = ""
    description: str = ""


@dataclass
class ListingRecord:
    external_id: str
    title: str
    property_type: str
    transaction_type: str
    price: Decimal
    source_url: str
    is_available: bool = True
    description: str = ""
    currency: str = "NGN"
    price_period: str = ""
    location: str = ""
    state: str = ""
    city: str = ""
    area: str = ""
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    toilets: Optional[int] = None
    furnished_status: str = "UNKNOWN"
    amenities: list = field(default_factory=list)
    image_urls: list = field(default_factory=list)
    # Some sources only expose the agency on a per-listing detail call; the
    # adapter can leave this empty and answer fetch_agency() on demand.
    agency: Optional[AgencyRecord] = None


class SourceAdapter:
    """Reads listings from one source. Subclasses must be side-effect free."""

    def __init__(self, source):
        self.source = source

    def iter_listings(self) -> Iterator[ListingRecord]:
        raise NotImplementedError

    def fetch_agency(self, listing: ListingRecord) -> Optional[AgencyRecord]:
        """Return the agency for a listing when iter_listings() didn't include it."""
        return listing.agency
