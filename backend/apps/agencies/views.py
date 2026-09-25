from rest_framework import viewsets
from rest_framework.permissions import AllowAny

from apps.properties.models import Property
from apps.properties.serializers import PropertyListSerializer

from .models import Agency
from .serializers import AgencyPublicSerializer


class AgencyPublicViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Public agency pages, e.g. GET /api/agencies/abc-realty/

    Only agencies that are not suspended and have at least reached
    PENDING_REVIEW are listable/visible; a purely DISCOVERED record with
    no admin eyes on it yet is not shown to customers.
    """

    queryset = Agency.objects.exclude(verification_status=Agency.VerificationStatus.DISCOVERED).exclude(is_suspended=True)
    serializer_class = AgencyPublicSerializer
    permission_classes = [AllowAny]
    lookup_field = "slug"

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx

    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)
        agency = self.get_object()
        active_properties = Property.objects.filter(
            agency=agency, status=Property.Status.ACTIVE
        ).select_related("agency")
        response.data["active_properties"] = PropertyListSerializer(
            active_properties, many=True, context=self.get_serializer_context()
        ).data
        return response
