"""
PropertySpot (propertyspot.com.ng) adapter.

Reads the same public JSON API the PropertySpot website itself uses:
  GET {API}/home/properties?purpose=rent|sale|shortlet&page=N&per_page=50
  GET {API}/home/property/<id>           (includes the listing's agent)

Privacy: PropertySpot's agent payload includes government ID fields
(nin, bvn, id_card_image, company_registration_number). We never read or
store those -- only the public contact fields in AGENT_FIELDS_USED.
"""
import logging
import re
import time
from decimal import Decimal, InvalidOperation

import requests

from .base import AgencyRecord, ListingRecord, SourceAdapter

logger = logging.getLogger("apps.sources")

API_BASE = "https://app.propertyspot.com.ng/api/v1/"
SITE_BASE = "https://propertyspot.com.ng/"
USER_AGENT = "WebloraBot/1.0 (+https://github.com/Oluwaseun-bit-ui/Weblora-Real-Estate-)"
PAGE_SIZE = 50
REQUEST_DELAY_SECONDS = 0.5  # be polite to the source's API
AGENT_FIELDS_USED = ("id", "first_name", "last_name", "company_name", "email", "phone_number", "address", "description")

PURPOSE_TO_TRANSACTION = {
    "rent": "RENT",
    "sale": "BUY",
    "shortlet": "SHORTLET",
}

# First match wins, so more specific words come first.
PROPERTY_TYPE_KEYWORDS = [
    ("DUPLEX", ("duplex",)),
    ("BUNGALOW", ("bungalow",)),
    ("TERRACE", ("terrace",)),
    ("COMMERCIAL", ("office", "shop", "warehouse", "commercial", "plaza", "hotel", "event hall")),
    ("APARTMENT", ("apartment", "flat", "studio", "self contain", "self-contain", "penthouse", "maisonette")),
    ("HOUSE", ("house", "mansion", "detached")),
]

PRICE_PERIODS = {"year": "year", "month": "month", "day": "night", "night": "night", "week": "week"}


def _int_or_none(value):
    try:
        return int(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def parse_price(value) -> Decimal:
    try:
        return Decimal(str(value).replace(",", "").strip() or "0")
    except InvalidOperation:
        return Decimal("0")


def infer_property_type(item, transaction_type) -> str:
    if str(item.get("is_land")) == "1":
        return "LAND"
    text = f"{item.get('title', '')} {item.get('description', '')[:300]}".lower()
    for property_type, words in PROPERTY_TYPE_KEYWORDS:
        if any(w in text for w in words):
            return property_type
    if transaction_type == "SHORTLET":
        return "SHORTLET"
    return "OTHER"


def infer_furnished(item) -> str:
    text = f"{item.get('title', '')} {item.get('description', '')}".lower()
    if "semi-furnished" in text or "semi furnished" in text:
        return "SEMI_FURNISHED"
    if "unfurnished" in text:
        return "UNFURNISHED"
    if "furnished" in text:
        return "FURNISHED"
    return "UNKNOWN"


def normalize_phone(phone) -> str:
    """Normalise Nigerian numbers to +234XXXXXXXXXX; leave anything else as typed."""
    digits = re.sub(r"\D", "", str(phone or ""))
    if len(digits) == 11 and digits.startswith("0"):
        return "+234" + digits[1:]
    if len(digits) == 13 and digits.startswith("234"):
        return "+" + digits
    return str(phone or "").strip()


def parse_listing(item, purpose) -> ListingRecord:
    transaction_type = PURPOSE_TO_TRANSACTION[purpose]
    location = item.get("location") or {}
    state = (location.get("state") or {}).get("name", "")
    area = location.get("name", "")

    amenities = []
    for group in item.get("amenities_by_category") or []:
        amenities.extend(a["name"].strip() for a in group.get("amenities") or [] if a.get("name"))

    images = [item["image"]] if item.get("image") else []
    images += [img["image"] for img in item.get("images") or [] if img.get("image") and img["image"] not in images]

    return ListingRecord(
        external_id=str(item["id"]),
        title=(item.get("title") or "").strip()[:500],
        description=item.get("description") or "",
        property_type=infer_property_type(item, transaction_type),
        transaction_type=transaction_type,
        price=parse_price(item.get("price")),
        price_period=PRICE_PERIODS.get(str(item.get("price_duration") or "").lower(), ""),
        location=(item.get("address") or area)[:255],
        state=state,
        city=state,
        area=area,
        bedrooms=_int_or_none(item.get("bedrooms")),
        bathrooms=_int_or_none(item.get("bathrooms")),
        furnished_status=infer_furnished(item),
        amenities=amenities,
        image_urls=images,
        is_available=item.get("status") == "available",
        source_url=f"{SITE_BASE}single-property.html?id={item['id']}",
    )


def parse_agent(agent) -> AgencyRecord | None:
    if not agent or not agent.get("id"):
        return None
    agent = {k: agent.get(k) for k in AGENT_FIELDS_USED}  # drop ID-document fields immediately
    person = " ".join(p for p in (agent["first_name"], agent["last_name"]) if p).strip()
    name = (agent["company_name"] or person or "PropertySpot agent").strip()
    phone = normalize_phone(agent["phone_number"])
    return AgencyRecord(
        external_id=str(agent["id"]),
        name=name.title() if name.islower() else name,
        phone_number=phone,
        whatsapp_number=phone.lstrip("+") if phone.startswith("+234") else "",
        email=(agent["email"] or "").strip(),
        business_address=(agent["address"] or "").strip()[:500],
        description=(agent["description"] or "").strip(),
    )


class PropertySpotAdapter(SourceAdapter):
    def __init__(self, source, session=None, delay=REQUEST_DELAY_SECONDS):
        super().__init__(source)
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})
        self.delay = delay

    def _get(self, path, params=None):
        resp = self.session.get(API_BASE + path, params=params, timeout=30)
        resp.raise_for_status()
        if self.delay:
            time.sleep(self.delay)
        return resp.json()

    def iter_listings(self):
        for purpose in PURPOSE_TO_TRANSACTION:
            page, last_page = 1, 1
            while page <= last_page:
                payload = self._get("home/properties", {"purpose": purpose, "page": page, "per_page": PAGE_SIZE})
                last_page = int((payload.get("meta") or {}).get("last_page") or 1)
                for item in payload.get("data") or []:
                    try:
                        yield parse_listing(item, purpose)
                    except (KeyError, TypeError, ValueError):
                        logger.warning("PropertySpot: skipping malformed listing %r", item.get("id"))
                page += 1

    def fetch_agency(self, listing):
        payload = self._get(f"home/property/{listing.external_id}")
        prop = (payload.get("data") or {}).get("property") or {}
        return parse_agent(prop.get("agent"))
