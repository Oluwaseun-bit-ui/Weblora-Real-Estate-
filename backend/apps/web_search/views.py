import logging

import requests
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .services import WebSearchNotConfigured, search_web

logger = logging.getLogger("apps.web_search")

ALLOWED_PARAMS = ("q", "location", "property_type", "transaction_type", "bedrooms", "furnished_status")


class WebSearchView(APIView):
    """
    GET /api/web-search/?location=Lekki&transaction_type=RENT&bedrooms=2

    Unverified results from the wider web (Brave Search), each with any
    contact details found on the page. Always returns 200 with an
    `available` flag so the search page degrades gracefully.
    """

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "web_search"

    def get(self, request):
        filters = {k: request.query_params.get(k, "") for k in ALLOWED_PARAMS}
        try:
            data = search_web(filters)
        except WebSearchNotConfigured:
            return Response({"available": False, "reason": "not_configured", "results": []})
        except requests.RequestException as exc:
            logger.warning("Web search failed: %s", exc)
            return Response({"available": False, "reason": "upstream_error", "results": []})
        return Response({"available": True, **data})
