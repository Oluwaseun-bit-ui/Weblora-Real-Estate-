from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(["GET"])
@permission_classes([AllowAny])
def public_config(request):
    """
    Small, non-secret config the frontend needs at boot: which map provider
    is active and its public (non-secret) client key, if any. Keeps the map
    vendor swappable without a frontend redeploy.
    """
    map_provider = settings.MAP_PROVIDER
    public_key = ""
    if map_provider == "mapbox":
        public_key = settings.MAPBOX_ACCESS_TOKEN
    elif map_provider == "google":
        public_key = settings.GOOGLE_MAPS_API_KEY

    return Response(
        {
            "map_provider": map_provider,
            "map_public_key": public_key,
            "live_viewing_enabled": settings.LIVE_VIEWING_PROVIDER != "none",
            "time_zone": settings.TIME_ZONE,
        }
    )
