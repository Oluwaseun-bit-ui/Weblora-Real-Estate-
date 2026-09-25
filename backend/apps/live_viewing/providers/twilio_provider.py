"""
Twilio Video provider stub. Twilio issues short-lived Access Tokens
(JWT-based, via `twilio.jwt.access_token`) granting a VideoGrant scoped to
a room name; rooms can be created implicitly (group rooms) or explicitly
via the REST API. Left as a documented stub -- fails loudly until
implemented rather than faking success.
"""
from django.conf import settings

from .base import LiveViewingProvider, RoomToken


class TwilioVideoProvider(LiveViewingProvider):
    name = "twilio"

    def __init__(self):
        self.account_sid = settings.TWILIO_ACCOUNT_SID
        self.api_key_sid = settings.TWILIO_API_KEY_SID
        self.api_key_secret = settings.TWILIO_API_KEY_SECRET
        if not (self.account_sid and self.api_key_sid and self.api_key_secret):
            raise RuntimeError(
                "Twilio provider selected but TWILIO_ACCOUNT_SID/TWILIO_API_KEY_SID/"
                "TWILIO_API_KEY_SECRET are not set."
            )

    def create_room(self, *, session_id: str) -> str:
        return f"viewing-{session_id}"

    def mint_token(self, *, room_id: str, identity: str, role: str, ttl_seconds: int = 600) -> RoomToken:
        raise NotImplementedError(
            "Twilio Video token minting is not wired up yet. Build an AccessToken with a "
            "VideoGrant(room=room_id), identity=identity, and ttl=ttl_seconds using the "
            "`twilio` Python SDK."
        )

    def end_room(self, *, room_id: str) -> None:
        return None
