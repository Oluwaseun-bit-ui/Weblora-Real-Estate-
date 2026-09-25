import django_filters as filters

from apps.agencies.models import Agency

from .models import Property


class PropertySearchFilter(filters.FilterSet):
    location = filters.CharFilter(method="filter_location")
    property_type = filters.MultipleChoiceFilter(choices=Property.PropertyType.choices)
    transaction_type = filters.ChoiceFilter(choices=Property.TransactionType.choices)
    min_price = filters.NumberFilter(field_name="price", lookup_expr="gte")
    max_price = filters.NumberFilter(field_name="price", lookup_expr="lte")
    bedrooms = filters.NumberFilter(field_name="bedrooms", lookup_expr="gte")
    bathrooms = filters.NumberFilter(field_name="bathrooms", lookup_expr="gte")
    furnished_status = filters.ChoiceFilter(choices=Property.FurnishedStatus.choices)
    amenities = filters.CharFilter(method="filter_amenities", help_text="Comma-separated amenity list; all must be present.")
    verified_agency = filters.BooleanFilter(method="filter_verified_agency")
    verification_status = filters.ChoiceFilter(choices=Property.VerificationStatus.choices)
    live_viewing_available = filters.BooleanFilter(field_name="live_viewing_available")
    q = filters.CharFilter(method="filter_fulltext", label="Free-text search")

    class Meta:
        model = Property
        fields = [
            "location",
            "property_type",
            "transaction_type",
            "min_price",
            "max_price",
            "bedrooms",
            "bathrooms",
            "furnished_status",
            "amenities",
            "verified_agency",
            "verification_status",
            "live_viewing_available",
            "q",
        ]

    def filter_location(self, queryset, name, value):
        from django.db.models import Q

        return queryset.filter(
            Q(location__icontains=value) | Q(city__icontains=value) | Q(area__icontains=value) | Q(state__icontains=value)
        )

    def filter_amenities(self, queryset, name, value):
        amenities = [a.strip() for a in value.split(",") if a.strip()]
        for amenity in amenities:
            queryset = queryset.filter(amenities__icontains=amenity)
        return queryset

    def filter_verified_agency(self, queryset, name, value):
        if value:
            return queryset.filter(agency__verification_status=Agency.VerificationStatus.VERIFIED)
        return queryset

    def filter_fulltext(self, queryset, name, value):
        from django.contrib.postgres.search import SearchQuery

        return queryset.filter(search_vector=SearchQuery(value, search_type="websearch"))
