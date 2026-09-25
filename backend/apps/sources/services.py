"""
Ingestion sync: pulls listings from an authorized PropertySource via its
adapter and upserts them into Agency / Property / PropertyImage.

Rules enforced here (not in adapters):
- Only active, AUTHORIZED sources are synced.
- Listings are matched by (source, source_property_id), agencies by
  (source, source_agency_id), so re-syncs update rather than duplicate.
- An agency an officer has already moved past DISCOVERED/PENDING_REVIEW is
  never overwritten by ingested data -- verification decisions win.
- A listing that disappears from a *complete* sync is marked STALE (not
  deleted); if it reappears later it goes back to ACTIVE.
- Price changes are recorded in PriceHistory.
"""
import logging
from dataclasses import dataclass
from datetime import timedelta

import requests
from django.db import transaction
from django.utils import timezone

from apps.agencies.models import Agency
from apps.properties.models import PriceHistory, Property, PropertyImage

from .ingestion import get_adapter
from .models import PropertySource

logger = logging.getLogger("apps.sources")

DEFAULT_SYNC_FREQUENCY_MINUTES = 24 * 60
EDITABLE_AGENCY_STATUSES = {Agency.VerificationStatus.DISCOVERED, Agency.VerificationStatus.PENDING_REVIEW}


@dataclass
class SyncResult:
    created: int = 0
    updated: int = 0
    marked_stale: int = 0
    agencies_created: int = 0
    errors: int = 0


def _contact_status(value, current):
    if current in (Agency.ContactFieldStatus.VERIFIED, Agency.ContactFieldStatus.FAILED):
        return current
    return Agency.ContactFieldStatus.PROVIDED if value else Agency.ContactFieldStatus.NOT_PROVIDED


def upsert_agency(source, record, result):
    agency = Agency.objects.filter(sources=source, source_agency_id=record.external_id).first()
    created = agency is None
    if created:
        agency = Agency(source_agency_id=record.external_id)
    elif agency.verification_status not in EDITABLE_AGENCY_STATUSES:
        return agency

    agency.name = record.name[:255]
    agency.phone_number = record.phone_number[:32]
    agency.email = record.email
    agency.whatsapp_number = record.whatsapp_number[:32]
    agency.business_address = record.business_address
    if record.website:
        agency.website = record.website
    if record.description and not agency.description:
        agency.description = record.description
    agency.phone_status = _contact_status(agency.phone_number, agency.phone_status)
    agency.email_status = _contact_status(agency.email, agency.email_status)
    if agency.website and agency.website_status == Agency.WebsiteStatus.NOT_PROVIDED:
        agency.website_status = Agency.WebsiteStatus.EXISTS
    agency.save()

    if created:
        agency.sources.add(source)
        result.agencies_created += 1
    return agency


def _sync_images(prop, urls, display_authorized):
    current = list(prop.images.exclude(external_url="").order_by("order").values_list("external_url", flat=True))
    if current == urls:
        return
    prop.images.exclude(external_url="").delete()
    PropertyImage.objects.bulk_create(
        [
            PropertyImage(property=prop, external_url=url, order=i, display_authorized=display_authorized)
            for i, url in enumerate(urls)
        ]
    )


def upsert_listing(source, adapter, record, result, agency_cache):
    now = timezone.now()
    prop = Property.objects.filter(source=source, source_property_id=record.external_id).first()
    created = prop is None
    if created:
        prop = Property(source=source, source_property_id=record.external_id)

    old_price = None if created else prop.price

    if created or prop.agency_id is None:
        try:
            agency_record = adapter.fetch_agency(record)
        except requests.RequestException as exc:
            logger.warning("Could not fetch agency for %s listing %s: %s", source.name, record.external_id, exc)
            agency_record = None
        if agency_record:
            if agency_record.external_id not in agency_cache:
                agency_cache[agency_record.external_id] = upsert_agency(source, agency_record, result)
            prop.agency = agency_cache[agency_record.external_id]

    for field in (
        "title", "description", "property_type", "transaction_type", "price", "currency", "price_period",
        "location", "state", "city", "area", "bedrooms", "bathrooms", "toilets", "furnished_status",
        "amenities", "source_url",
    ):
        setattr(prop, field, getattr(record, field))
    prop.status = Property.ListingStatus.ACTIVE if record.is_available else Property.ListingStatus.REMOVED
    prop.verification_status = Property.VerificationStatus.SOURCE_CONFIRMED
    prop.last_seen_at = now
    prop.last_checked_at = now
    prop.save()

    if old_price is not None and old_price != record.price:
        PriceHistory.objects.create(property=prop, price=old_price, currency=prop.currency)

    _sync_images(prop, record.image_urls, source.permission_status == PropertySource.PermissionStatus.AUTHORIZED)

    if created:
        result.created += 1
    else:
        result.updated += 1


def sync_source(source, adapter=None) -> SyncResult:
    if not source.is_active or source.permission_status != PropertySource.PermissionStatus.AUTHORIZED:
        raise ValueError(f"Source {source.name!r} is not active and AUTHORIZED; refusing to ingest.")

    adapter = adapter or get_adapter(source)
    result = SyncResult()
    seen_ids = set()
    agency_cache = {}

    for record in adapter.iter_listings():
        seen_ids.add(record.external_id)
        try:
            with transaction.atomic():
                upsert_listing(source, adapter, record, result, agency_cache)
        except Exception:
            result.errors += 1
            logger.exception("Failed to ingest %s listing %s", source.name, record.external_id)

    # Only reached when the adapter finished iterating, i.e. we saw the
    # source's complete listing set -- safe to treat missing ones as stale.
    result.marked_stale = (
        Property.objects.filter(source=source, status=Property.ListingStatus.ACTIVE)
        .exclude(source_property_id__in=seen_ids)
        .update(status=Property.ListingStatus.STALE, verification_status=Property.VerificationStatus.STALE)
    )

    now = timezone.now()
    source.last_synced_at = now
    source.next_sync_at = now + timedelta(minutes=source.sync_frequency_minutes or DEFAULT_SYNC_FREQUENCY_MINUTES)
    source.save(update_fields=["last_synced_at", "next_sync_at", "updated_at"])

    logger.info("Synced %s: %s", source.name, result)
    return result


def sync_due_sources():
    now = timezone.now()
    due = PropertySource.objects.filter(
        is_active=True, permission_status=PropertySource.PermissionStatus.AUTHORIZED
    ).exclude(adapter="")
    results = {}
    for source in due:
        if source.next_sync_at and source.next_sync_at > now:
            continue
        try:
            results[source.name] = sync_source(source)
        except Exception:
            logger.exception("Sync failed for source %s", source.name)
    return results
