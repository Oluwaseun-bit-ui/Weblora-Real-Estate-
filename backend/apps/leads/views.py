from django.utils import timezone
from rest_framework import mixins, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.throttling import AnonRateThrottle

from .models import Lead
from .serializers import LeadCreateSerializer


class LeadSubmitThrottle(AnonRateThrottle):
    scope = "lead_submit"


class LeadCreateViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """
    POST /api/leads/  -- customer submits an enquiry, which is a referral
    to the agency, not a transaction the platform fulfils itself.
    """

    serializer_class = LeadCreateSerializer
    permission_classes = [AllowAny]
    throttle_classes = [LeadSubmitThrottle]
    queryset = Lead.objects.none()

    def perform_create(self, serializer):
        lead = serializer.save(status=Lead.Status.NEW)
        # In a full implementation this would enqueue a Celery task to
        # notify the agency (email/SMS/WhatsApp) and flip status to SENT
        # once delivered. Kept synchronous + simple for the MVP boundary.
        lead.status = Lead.Status.SENT
        lead.referred_at = timezone.now()
        lead.save(update_fields=["status", "referred_at", "updated_at"])
