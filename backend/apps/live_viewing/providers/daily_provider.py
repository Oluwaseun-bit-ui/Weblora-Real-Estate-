"""
Daily.co provider stub. Daily's REST API creates a room (POST /rooms) and
mints meeting tokens (POST /meeting-tokens) using a server-side API key.
Left as a documented stub -- fails loudly until implemented rather than
faking success.
"""
from django.conf import settings

from .base import LiveViewingProvider, RoomToken


class DailyProvider(LiveViewingProvider):
    name = "daily"

    def __init__(self):
        self.api_key = settings.DAILY_API_KEY
        if not self.api_key:
            raise RuntimeError("Daily provider selected but DAILY_API_KEY is not set.")

    def create_room(self, *, session_id: str) -> str:
        raise NotImplementedError(
            "Daily room creation is not wired up yet. POST to https://api.daily.co/v1/rooms "
            "with the API key, using a private room + short `exp` for auto-expiry."
        )

    def mint_token(self, *, room_id: str, identity: str, role: str, ttl_seconds: int = 600) -> RoomToken:
        raise NotImplementedError(
            "Daily meeting token minting is not wired up yet. POST to "
            "https://api.daily.co/v1/meeting-tokens with room_name and exp=now+ttl_seconds."
        )

    def end_room(self, *, room_id: str) -> None:
        return None
