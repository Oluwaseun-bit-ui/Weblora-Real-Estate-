"""
Notification dispatch for live viewing lifecycle events. Email is the only
implemented channel for the MVP; WhatsApp/SMS/push are modular hooks that
can be added by implementing `NotificationChannel` and registering it in
`CHANNELS` without touching call sites.
"""
import logging

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger("apps.live_viewing")

EVENT_SUBJECTS = {
    "request_created": "New live viewing request",
    "request_accepted": "Your live viewing request was accepted",
    "request_declined": "Your live viewing request was declined",
    "viewing_reminder": "Reminder: your live property viewing is coming up",
    "viewing_starting_soon": "Your live property viewing starts soon",
    "viewing_started": "Your live property viewing has started",
    "viewing_completed": "Your live property viewing has ended",
    "viewing_cancelled": "Your live property viewing was cancelled",
}


class NotificationChannel:
    def send(self, *, to_email: str, to_phone: str, event: str, context: dict):
        raise NotImplementedError


class EmailChannel(NotificationChannel):
    def send(self, *, to_email: str, to_phone: str, event: str, context: dict):
        if not to_email:
            return
        subject = EVENT_SUBJECTS.get(event, "Live viewing update")
        body = context.get("message", subject)
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [to_email], fail_silently=True)


class WhatsAppChannel(NotificationChannel):
    """Placeholder -- not implemented for MVP. Wire up a WhatsApp Business API provider here."""

    def send(self, *, to_email: str, to_phone: str, event: str, context: dict):
        logger.info("[stub] Would send WhatsApp notification for %s to %s", event, to_phone)


class SMSChannel(NotificationChannel):
    """Placeholder -- not implemented for MVP. Wire up an SMS provider (Termii, Twilio, etc.) here."""

    def send(self, *, to_email: str, to_phone: str, event: str, context: dict):
        logger.info("[stub] Would send SMS notification for %s to %s", event, to_phone)


CHANNELS = [EmailChannel()]  # add WhatsAppChannel()/SMSChannel() once implemented


def notify(*, to_email: str = "", to_phone: str = "", event: str, context: dict = None):
    context = context or {}
    for channel in CHANNELS:
        try:
            channel.send(to_email=to_email, to_phone=to_phone, event=event, context=context)
        except Exception:  # noqa: BLE001
            logger.exception("Notification channel %s failed for event %s", channel.__class__.__name__, event)
