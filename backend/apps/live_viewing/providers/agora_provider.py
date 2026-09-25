"""
Agora provider stub. Agora tokens are minted with `agora-token-builder`
(or the official `agora_token_builder` package) using App ID + App
Certificate; rooms ("channels") don't need server-side creation, they're
created implicitly on join, so `create_room` just returns a channel name.

Left as a documented stub (raises until implemented) rather than a fake
success path -- selecting `agora` without finishing this integration must
fail loudly, not pretend to work.
"""
from django.conf import settings

from .base import LiveViewingProvider, RoomToken


class AgoraProvider(LiveViewingProvider):
    name = "agora"

    def __init__(self):
        self.app_id = settings.AGORA_APP_ID
        self.app_certificate = settings.AGORA_APP_CERTIFICATE
        if not (self.app_id and self.app_certificate):
            raise RuntimeError("Agora provider selected but AGORA_APP_ID/AGORA_APP_CERTIFICATE are not set.")

    def create_room(self, *, session_id: str) -> str:
        return f"viewing-{session_id}"

    def mint_token(self, *, room_id: str, identity: str, role: str, ttl_seconds: int = 600) -> RoomToken:
        raise NotImplementedError(
            "Agora token minting is not wired up yet. Install `agora-token-builder`, generate an "
            "RTC token here with app_id/app_certificate, room_id as channel name, and return it."
        )

    def end_room(self, *, room_id: str) -> None:
        return None
