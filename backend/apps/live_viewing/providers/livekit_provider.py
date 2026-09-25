"""
LiveKit provider implementation.

LiveKit's Python SDK (`livekit-api`) issues JWT access tokens signed with an
API key/secret and can create rooms via its server API. We keep the
dependency optional (imported lazily) since not every deployment will use
LiveKit -- see AgoraProvider/DailyProvider/TwilioVideoProvider siblings for
the same pattern with other vendors. Only one is active at a time, chosen
via settings.LIVE_VIEWING_PROVIDER.
"""
from django.conf import settings

from .base import LiveViewingProvider, RoomToken


class LiveKitProvider(LiveViewingProvider):
    name = "livekit"

    def __init__(self):
        self.api_key = settings.LIVEKIT_API_KEY
        self.api_secret = settings.LIVEKIT_API_SECRET
        self.url = settings.LIVEKIT_URL
        if not (self.api_key and self.api_secret and self.url):
            raise RuntimeError("LiveKit provider selected but LIVEKIT_API_KEY/LIVEKIT_API_SECRET/LIVEKIT_URL are not set.")

    def create_room(self, *, session_id: str) -> str:
        # LiveKit rooms can be created lazily on first join, but creating
        # explicitly lets us control naming/TTL up front.
        from livekit import api  # local import: optional dependency

        room_name = f"viewing-{session_id}"
        client = api.LiveKitAPI(self.url, self.api_key, self.api_secret)
        client.room.create_room(api.CreateRoomRequest(name=room_name, empty_timeout=15 * 60))
        return room_name

    def mint_token(self, *, room_id: str, identity: str, role: str, ttl_seconds: int = 600) -> RoomToken:
        from livekit import api  # local import: optional dependency

        token = (
            api.AccessToken(self.api_key, self.api_secret)
            .with_identity(identity)
            .with_name(role)
            .with_grants(api.VideoGrants(room_join=True, room=room_id))
            .with_ttl(ttl_seconds)
        )
        return RoomToken(
            room_id=room_id,
            token=token.to_jwt(),
            provider=self.name,
            expires_in_seconds=ttl_seconds,
            identity=identity,
            role=role,
        )

    def end_room(self, *, room_id: str) -> None:
        from livekit import api  # local import: optional dependency

        client = api.LiveKitAPI(self.url, self.api_key, self.api_secret)
        client.room.delete_room(api.DeleteRoomRequest(room=room_id))
