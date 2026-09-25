import logging
import time

logger = logging.getLogger("apps.core")


class RequestLoggingMiddleware:
    """Lightweight structured request logging (method, path, status, latency).

    Kept dependency-free; a hosted logging/observability stack can replace
    this later without touching application code.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.monotonic()
        response = self.get_response(request)
        duration_ms = (time.monotonic() - start) * 1000
        logger.info(
            "%s %s -> %s (%.1fms)",
            request.method,
            request.path,
            response.status_code,
            duration_ms,
        )
        return response
