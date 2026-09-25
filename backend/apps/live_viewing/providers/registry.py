from django.conf import settings

from .agora_provider import AgoraProvider
from .base import LiveViewingProvider, NullProvider
from .daily_provider import DailyProvider
from .livekit_provider import LiveKitProvider
from .twilio_provider import TwilioVideoProvider

_PROVIDERS = {
    "livekit": LiveKitProvider,
    "agora": AgoraProvider,
    "daily": DailyProvider,
    "twilio": TwilioVideoProvider,
    "none": NullProvider,
}


def get_live_viewing_provider() -> LiveViewingProvider:
    provider_key = settings.LIVE_VIEWING_PROVIDER
    provider_cls = _PROVIDERS.get(provider_key, NullProvider)
    return provider_cls()
