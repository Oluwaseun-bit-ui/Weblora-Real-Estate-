"""
Live viewing lifecycle logic. Kept out of views so both the DRF API and the
admin dashboard use the same rules, and so the backend -- not the video
provider -- owns authentication, authorization, scheduling and audit
logging (per the product spec: the provider only handles media transport).
"""
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone

from apps.core.models import log_action

from .models import LiveViewingEvent, LiveViewingRequest, LiveViewingSession
from .notifications import notify
from .providers.registry import get_live_viewing_provider


def _log_event(viewing_request: LiveViewingRequest, event_type: str, detail: dict = None):
    LiveViewingEvent.objects.create(viewing_request=viewing_request, event_type=event_type, detail=detail or {})


def request_live_viewing(*, property_obj, customer_name, customer_email, customer_phone, requested_date, requested_time, message=""):
    if not property_obj.live_viewing_available or not property_obj.agency_id:
        raise ValueError("Live viewing is not available for this property.")

    viewing_request = LiveViewingRequest.objects.create(
        property=property_obj,
        agency=property_obj.agency,
        customer_name=customer_name,
        customer_email=customer_email,
        customer_phone=customer_phone,
        requested_date=requested_date,
        requested_time=requested_time,
        customer_message=message,
        status=LiveViewingRequest.Status.PENDING_AGENT,
    )
    _log_event(viewing_request, "request_created")
    notify(
        to_email=viewing_request.agency.email,
        to_phone=viewing_request.agency.phone_number,
        event="request_created",
        context={"message": f"New live viewing request for {property_obj.title} from {customer_name}."},
    )
    return viewing_request


@transaction.atomic
def accept_request(viewing_request: LiveViewingRequest, *, representative, actor=None, scheduled_start=None, scheduled_end=None):
    if viewing_request.status not in {LiveViewingRequest.Status.REQUESTED, LiveViewingRequest.Status.PENDING_AGENT}:
        raise ValueError(f"Cannot accept a request in status {viewing_request.status}.")

    now = timezone.now()
    scheduled_start = scheduled_start or now + timedelta(hours=1)
    scheduled_end = scheduled_end or scheduled_start + timedelta(minutes=30)

    viewing_request.status = LiveViewingRequest.Status.SCHEDULED
    viewing_request.accepted_at = now
    viewing_request.representative = representative
    viewing_request.save(update_fields=["status", "accepted_at", "representative", "updated_at"])

    session = LiveViewingSession.objects.create(
        viewing_request=viewing_request,
        provider_name=settings.LIVE_VIEWING_PROVIDER,
        scheduled_start=scheduled_start,
        scheduled_end=scheduled_end,
        status=LiveViewingSession.Status.SCHEDULED,
    )

    _log_event(viewing_request, "request_accepted", {"representative": representative.name if representative else None})
    log_action(actor=actor, action="live_viewing.accepted", obj=viewing_request)
    notify(
        to_email=viewing_request.customer_email,
        to_phone=viewing_request.customer_phone,
        event="request_accepted",
        context={"message": f"Your live viewing for {viewing_request.property.title} is scheduled."},
    )
    return session


def decline_request(viewing_request: LiveViewingRequest, *, reason: str = "", actor=None):
    viewing_request.status = LiveViewingRequest.Status.DECLINED
    viewing_request.decline_reason = reason
    viewing_request.save(update_fields=["status", "decline_reason", "updated_at"])
    _log_event(viewing_request, "request_declined", {"reason": reason})
    log_action(actor=actor, action="live_viewing.declined", obj=viewing_request, notes=reason)
    notify(
        to_email=viewing_request.customer_email,
        to_phone=viewing_request.customer_phone,
        event="request_declined",
        context={"message": f"Your live viewing request for {viewing_request.property.title} was declined."},
    )


def _identity_for(viewing_request: LiveViewingRequest, role: str) -> str:
    # Opaque per-session identity; never embeds raw PII in the token/room.
    return f"{role}:{viewing_request.id}"


def join_as_customer(viewing_request: LiveViewingRequest, *, access_token: str):
    """
    Authorizes and mints a join credential for the CUSTOMER side. The
    access_token must match the one generated for this specific booking
    (sent to the customer via email/SMS), which prevents one customer from
    joining another customer's viewing -- there is no public/guessable room
    link.
    """
    if access_token != viewing_request.customer_access_token:
        raise PermissionDenied("Invalid or expired viewing access token.")
    return _join(viewing_request, role="customer")


def join_as_representative(viewing_request: LiveViewingRequest, *, representative):
    if not representative or representative.agency_id != viewing_request.agency_id or not representative.is_active:
        raise PermissionDenied("This representative is not authorized to join this viewing.")
    if viewing_request.representative_id and viewing_request.representative_id != representative.id:
        raise PermissionDenied("A different representative is assigned to this viewing.")
    return _join(viewing_request, role="agent")


def _join(viewing_request: LiveViewingRequest, *, role: str):
    session = getattr(viewing_request, "session", None)
    if not session or viewing_request.status not in {
        LiveViewingRequest.Status.SCHEDULED,
        LiveViewingRequest.Status.LIVE,
    }:
        raise ValueError("This viewing is not currently joinable.")

    provider = get_live_viewing_provider()
    if not session.provider_room_id:
        session.provider_room_id = provider.create_room(session_id=str(session.id))
        session.provider_name = provider.name
        session.save(update_fields=["provider_room_id", "provider_name", "updated_at"])

    if session.status == LiveViewingSession.Status.SCHEDULED:
        session.status = LiveViewingSession.Status.LIVE
        session.actual_start = timezone.now()
        session.save(update_fields=["status", "actual_start", "updated_at"])
        viewing_request.status = LiveViewingRequest.Status.LIVE
        viewing_request.started_at = session.actual_start
        viewing_request.save(update_fields=["status", "started_at", "updated_at"])
        _log_event(viewing_request, "viewing_started")
        notify(
            to_email=viewing_request.customer_email,
            event="viewing_started",
            context={"message": "Your live property viewing has started."},
        )

    token = provider.mint_token(
        room_id=session.provider_room_id,
        identity=_identity_for(viewing_request, role),
        role=role,
        ttl_seconds=600,
    )
    return session, token


def end_session(viewing_request: LiveViewingRequest, *, actor=None):
    session = getattr(viewing_request, "session", None)
    if session:
        session.status = LiveViewingSession.Status.COMPLETED
        session.actual_end = timezone.now()
        session.save(update_fields=["status", "actual_end", "updated_at"])
        provider = get_live_viewing_provider()
        try:
            provider.end_room(room_id=session.provider_room_id)
        except NotImplementedError:
            pass

    viewing_request.status = LiveViewingRequest.Status.COMPLETED
    viewing_request.ended_at = timezone.now()
    viewing_request.save(update_fields=["status", "ended_at", "updated_at"])
    _log_event(viewing_request, "viewing_completed")
    log_action(actor=actor, action="live_viewing.completed", obj=viewing_request)
    notify(to_email=viewing_request.customer_email, event="viewing_completed", context={"message": "Your live viewing has ended."})


def mark_no_shows():
    """
    Intended to run periodically (Celery beat). Any SCHEDULED viewing whose
    session start time is more than LIVE_VIEWING_NO_SHOW_TIMEOUT_MINUTES in
    the past, and which never went LIVE, is marked NO_SHOW so the customer
    isn't left waiting indefinitely and can reschedule.
    """
    cutoff = timezone.now() - timedelta(minutes=settings.LIVE_VIEWING_NO_SHOW_TIMEOUT_MINUTES)
    stuck = LiveViewingRequest.objects.filter(
        status=LiveViewingRequest.Status.SCHEDULED, session__scheduled_start__lt=cutoff
    )
    for viewing_request in stuck:
        viewing_request.status = LiveViewingRequest.Status.NO_SHOW
        viewing_request.save(update_fields=["status", "updated_at"])
        session = getattr(viewing_request, "session", None)
        if session:
            session.status = LiveViewingSession.Status.FAILED
            session.save(update_fields=["status", "updated_at"])
        _log_event(viewing_request, "no_show")
        notify(
            to_email=viewing_request.customer_email,
            event="viewing_cancelled",
            context={"message": "The agent did not join your live viewing in time. You can request a new time."},
        )
