"""
Real-time video provider abstraction for live property viewings.

We do NOT implement WebRTC signalling/media relay ourselves -- that's a
reputable managed provider's job (LiveKit, Agora, Daily, Twilio Video, or
another WebRTC-compatible service). The backend's job, done by
`LiveViewingProvider` implementations, is:

  - create a room for a session
  - mint short-lived, single-purpose join tokens (never a permanent room
    credential)
  - tear the room down / invalidate tokens when the session ends

Everything else (authentication of *who* may request a token, authorization
of which room they may join, scheduling, notifications, audit logging)
stays in application code (`apps/live_viewing/services.py` and views), so
swapping providers never touches those concerns.
"""
from __future__ import annotations

import dataclasses


@dataclasses.dataclass
class RoomToken:
    room_id: str
    token: str
    provider: str
    expires_in_seconds: int
    identity: str
    role: str  # "customer" | "agent"


class LiveViewingProvider:
    """Interface every real-time video backend must implement."""

    name: str = ""

    def create_room(self, *, session_id: str) -> str:
        """Creates (or reuses) a room for this session and returns its provider-side room id."""
        raise NotImplementedError

    def mint_token(self, *, room_id: str, identity: str, role: str, ttl_seconds: int = 600) -> RoomToken:
        """
        Mints a short-lived join credential. `identity` should be an opaque
        per-participant id (never raw PII beyond a display name), `role`
        distinguishes customer vs agent so the provider/frontend can apply
        different UI affordances if needed. Tokens MUST be short-lived
        (default 10 minutes) -- the caller re-mints if the viewer needs to
        reconnect after that window.
        """
        raise NotImplementedError

    def end_room(self, *, room_id: str) -> None:
        """Closes the room and invalidates any outstanding tokens where the provider supports it."""
        raise NotImplementedError


class NullProvider(LiveViewingProvider):
    """
    Used when LIVE_VIEWING_PROVIDER=none (default). Fails loudly rather than
    pretending to create a working video session, so the feature visibly
    stays "coming soon" in an environment with no provider configured
    instead of silently breaking at join time.
    """

    name = "none"

    def create_room(self, *, session_id: str) -> str:
        raise NotImplementedError(
            "No real-time video provider is configured. Set LIVE_VIEWING_PROVIDER "
            "to one of: livekit, agora, daily, twilio, and provide its credentials."
        )

    def mint_token(self, *, room_id: str, identity: str, role: str, ttl_seconds: int = 600) -> RoomToken:
        raise NotImplementedError("No real-time video provider is configured.")

    def end_room(self, *, room_id: str) -> None:
        return None
