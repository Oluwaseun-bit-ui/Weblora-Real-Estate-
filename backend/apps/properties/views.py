from rest_framework import viewsets
from rest_framework.permissions import AllowAny

from .filters import PropertySearchFilter
from .models import Property
from .serializers import PropertyDetailSerializer, PropertyListSerializer

SORT_OPTIONS = {
    "relevance": ("-is_featured", "-discovered_at"),
    "newest": ("-discovered_at",),
    "price_asc": ("price",),
    "price_desc": ("-price",),
}


class PropertySearchViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Customer-facing property search API.

    GET /api/properties/?location=Lekki&property_type=APARTMENT&transaction_type=RENT
        &min_price=2000000&max_price=8000000&bedrooms=2&amenities=pool,gym
        &furnished_status=FURNISHED&verified_agency=true&sort=price_asc

    Only ACTIVE, non-removed listings are searchable by customers. Featured
    listings are boosted only under the "relevance" sort and are always
    labelled `is_featured` in the response so the UI can show a
    "Sponsored"/"Featured" badge -- ranking is never pay-to-win silently.
    """

    serializer_class = PropertyListSerializer
    permission_classes = [AllowAny]
    filterset_class = PropertySearchFilter

    def get_queryset(self):
        qs = Property.objects.filter(status=Property.ListingStatus.ACTIVE).select_related("agency", "source").prefetch_related("images")
        sort = self.request.query_params.get("sort", "relevance")
        ordering = SORT_OPTIONS.get(sort, SORT_OPTIONS["relevance"])
        return qs.order_by(*ordering)

    def get_serializer_class(self):
        if self.action == "retrieve":
            return PropertyDetailSerializer
        return PropertyListSerializer

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx
