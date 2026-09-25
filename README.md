# Property Discovery & Verification Platform (Lagos MVP)

A customer-first property discovery platform for the Nigerian market. Customers
search for apartments, houses, land and shortlets; the platform connects them
with **verified** real-estate agencies. Agencies are never required to
register — they are discovered or manually onboarded, and earn a verification
status through an auditable workflow.

> **Build note:** this was generated in an environment without outbound
> access to PyPI/npm (both registries returned HTTP 403 here), so the code
> could be written and syntax-checked (`python3 -m py_compile` passes on
> every backend file) but not installed, migrated, or run end-to-end in this
> session. See **Getting started** below to run it in your own environment.

## 1. Architecture summary

**Backend:** Django 5 + Django REST Framework + PostgreSQL, organized as
small apps under `backend/apps/`:

| App | Responsibility |
|---|---|
| `core` | Shared base model (UUID pk + timestamps), `AuditLog`, request logging middleware, public non-secret config endpoint |
| `accounts` | Staff/admin `User` model with roles (superadmin, verification officer, support); customers do **not** need accounts |
| `sources` | `PropertySource` — where data comes from, its authorization/permission status, and its allowed ingestion method |
| `agencies` | `Agency` — verification status, contact-verification fields, regulatory registration numbers, evidence-backed badges |
| `properties` | `Property`, `PropertyImage`, `PriceHistory` — listings, search (Postgres full-text + filters), stale-listing tracking |
| `verification` | `VerificationCheck`, `RegulatoryRecord`, and the **provider abstraction** (ESVARBON/LASRERA/CAC/Contact/Website) |
| `leads` | `Lead` — customer enquiries referred to agencies, with consent and status workflow |
| `live_viewing` | `LiveViewingRequest`, `LiveViewingSession`, `AgencyRepresentative`, and the **video provider abstraction** (LiveKit/Agora/Daily/Twilio) |

**Frontend:** React + Vite (`frontend/`) — property search, property detail
(with live-viewing request + enquiry forms), and public agency pages.

**Background jobs:** Celery + Redis, wired up (`config/celery.py`,
`apps/live_viewing/tasks.py`) with a no-show sweep task as the first
consumer; ingestion sync tasks are the natural next addition in Phase 3.

**Images:** served via Django's storage abstraction; `USE_S3=True` switches
to any S3-compatible bucket (AWS S3, DigitalOcean Spaces, Cloudflare R2) —
nothing is ever stored as a blob in Postgres.

**Maps:** `MAP_PROVIDER` env var + `/api/config/` endpoint lets the frontend
pick up whichever provider (Mapbox, Google, or a free provider like
MapLibre/OSM) is configured, without hard-coding a vendor into the app.

### Why a provider abstraction for verification and for live video

Both are built the same way for the same reason: **the specific
regulator/vendor must be swappable without redesigning the app.**

- `apps/verification/providers/base.py` defines `VerificationProvider`.
  `ESVARBONProvider`, `LASRERAProvider`, `CACProvider`,
  `ContactVerificationProvider`, `WebsiteVerificationProvider` each
  implement it. **None of ESVARBON/LASRERA/CAC claim to be automated** —
  no confirmed public API exists for any of them at the time of writing, so
  `is_automated = False` and each provider instead supplies
  `official_source_url()` + `manual_instructions()` for a human
  verification officer, and `build_manual_check_kwargs()` to record what
  they found as a `VerificationCheck` with `method=MANUAL_PORTAL_CHECK`.
  `VerificationCheck.clean()` actively **rejects** attempts to mark an
  ESVARBON/LASRERA check as `AUTOMATED_API`, so the system cannot silently
  mislabel a manual result. `WebsiteVerificationProvider` automates only
  the narrow, clearly-permitted part (checking a URL responds), never the
  "matches agency identity" judgement call.
- `apps/live_viewing/providers/base.py` defines `LiveViewingProvider`
  (`create_room` / `mint_token` / `end_room`). `LiveKitProvider` is
  implemented against the LiveKit server SDK; `AgoraProvider`,
  `DailyProvider`, `TwilioVideoProvider` are documented stubs that raise
  `NotImplementedError` rather than pretending to work, so picking an
  unfinished provider fails loudly. Auth, authorization (who may join which
  room), scheduling, and audit logging all live in
  `apps/live_viewing/services.py` — never in the provider — so swapping
  video vendors never touches those concerns.

### Product rules enforced in code, not just docs

- `Agency.has_sufficient_contact_info` + `verification/services.approve_agency`
  refuse to grant `VERIFIED` status without enough *verified* (not just
  provided) contact channels.
- `Agency.verification_badges()` only returns a badge (e.g. "ESVARBON
  Verified") if there's a `VerificationCheck` with `result=PASS` backing it
  — never a generic "100% trusted" claim.
- `PropertySource.clean()` refuses to activate an API/feed source that
  isn't `AUTHORIZED` (manual entry is exempt, since an admin typing a
  listing by hand needs no external authorization).
- Property listing status (`ACTIVE`/`STALE`/`REMOVED`/`PENDING_REVIEW`) and
  verification status (`SOURCE_CONFIRMED`/`AGENCY_PROVIDED`/
  `INDEPENDENTLY_VERIFIED`/...) are **separate fields** — agency
  verification never implies property verification.
- Search sorting only boosts `is_featured` listings under `sort=relevance`,
  and every result always carries `is_featured` so the UI can label it —
  ranking is never pay-to-win silently.
- Live viewing join is gated by a per-booking secret token
  (customer side) or an agency-scoped `AgencyRepresentative` record (agent
  side); there is no public/guessable room link, and tokens are minted
  short-lived (10 minutes) per join.

## 2. Database schema (selected models)

```
PropertySource
  name, url, source_type, ingestion_method, permission_status,
  is_active, last_synced_at, next_sync_at

Agency
  name, slug, website, phone/email/whatsapp, business_address,
  service_locations[], cac/esvarbon/lasrera registration numbers,
  verification_status, verification_recheck_date,
  phone_status, email_status, website_status,
  sources -> M2M PropertySource

VerificationCheck
  agency -> FK, check_type, method, source, result,
  registration_number, subject_name, evidence_reference, evidence_file,
  checked_at, checked_by -> FK User, expiration_date, recheck_date

RegulatoryRecord
  regulator, registration_number, subject_name, status_on_registry,
  raw_reference, source_url, checked_at, verification_check -> FK

Property
  title, description, property_type, transaction_type, price, currency,
  location/state/city/area, latitude/longitude, bedrooms/bathrooms/toilets,
  amenities[], furnished_status, agency -> FK, source -> FK, source_url,
  source_property_id, status, verification_status,
  discovered_at, last_checked_at, last_seen_at,
  is_featured, live_viewing_available, search_vector (GIN indexed)

PropertyImage       -- property -> FK, image, display_authorized, order
PriceHistory         -- property -> FK, price, recorded_at

Lead
  property -> FK, agency -> FK, customer_name/email/phone, message,
  source_channel, status, consent_given, consent_timestamp, referred_at

LiveViewingRequest
  property -> FK, agency -> FK, representative -> FK,
  customer_name/email/phone, requested_date/time, customer_message,
  status, accepted_at/started_at/ended_at, customer_access_token

LiveViewingSession
  viewing_request -> 1:1, provider_name, provider_room_id,
  scheduled_start/end, actual_start/end, status, recording_enabled

AgencyRepresentative  -- agency -> FK, name, phone, email, is_active
LiveViewingEvent       -- viewing_request -> FK, event_type, detail, occurred_at

AuditLog
  actor -> FK User, action, object_type, object_id,
  previous_value, new_value, notes, timestamp
```

## 3. Implementation plan status

- **Phase 1** (architecture, models, admin, search API, search UI) — **done** in this build.
- **Phase 2** (ESVARBON/LASRERA providers, contact verification workflow,
  agency public pages, verification badges) — **done**: manual-first
  providers + admin verification queue + public agency pages + badges.
- **Phase 3** (property ingestion, source management, stale detection, lead
  generation) — **partially done**: models/admin/stale-marking actions and
  the full leads flow are in; the actual ingestion connectors (calling a
  specific partner API/feed) are intentionally left unimplemented since no
  real source/partnership was specified — `PropertySource` + `Property`
  are ready for a Celery task per source to be added.
- **Phase 4** (advanced search/Elasticsearch, maps UI, WhatsApp/contact
  integrations, analytics, featured listings, monetization) — scaffolded
  where cheap to do so (maps provider config, featured-listing labelling,
  WhatsApp click-through) and otherwise left for a follow-up milestone.
- **Live viewing** (the real-time video feature) — **done** end-to-end for
  the MVP boundary described: request → accept → scheduled session → join
  tokens → live → complete/no-show, with LiveKit implemented and
  Agora/Daily/Twilio as documented stubs.

## 4. Getting started

Requires network access to PyPI and npm (unavailable in the session that
generated this code — see the build note above).

```bash
cp backend/.env.example backend/.env      # edit DB creds, provider keys, etc.
cp frontend/.env.example frontend/.env

# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver

# Frontend (separate shell)
cd frontend
npm install
npm run dev
```

Or via Docker: `docker compose up --build` (after filling in `backend/.env`).

Run tests: `cd backend && pytest` (needs a Postgres instance reachable per
`.env`; `pytest-django` + `factory-boy` are already in `requirements.txt`).

Admin dashboard: `http://localhost:8000/admin/` — Agencies, Properties,
Sources, Verification (checks + regulatory records), Leads, Live Viewing,
Users, Audit Log all register there with list filters/actions matching the
verification-queue and stale-listing workflows described in the spec.

## 5. What to wire up next (explicitly out of scope here)

1. **Real ingestion connectors** — one Celery task per `PropertySource`
   that respects its `ingestion_method`; the source/property models and
   stale-detection fields are ready for this.
2. **A confirmed OTP provider** for automated phone/email verification
   (currently a recorded manual/semi-manual workflow via
   `ContactVerificationProvider`).
3. **Finishing Agora/Daily/Twilio** token minting if LiveKit isn't the
   chosen vendor (LiveKit is the only provider with real SDK calls wired
   in; the others raise `NotImplementedError` on purpose).
4. **Elasticsearch/OpenSearch** if Postgres full-text search stops scaling
   — the `PropertySearchFilter`/`search_vector` design isolates this swap
   to `apps/properties/filters.py` and the search viewset.
5. **Payments/monetization** for featured listings — intentionally left
   modular (`Property.is_featured` exists; no payment code was added).
