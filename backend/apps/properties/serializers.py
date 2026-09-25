from rest_framework import serializers

from apps.agencies.serializers import AgencyMinimalSerializer

from .models import Property, PropertyImage


class PropertyImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = PropertyImage
        fields = ["id", "image_url", "caption", "order"]

    def get_image_url(self, obj):
        if not obj.display_authorized:
            return None
        request = self.context.get("request")
        url = obj.image.url
        return request.build_absolute_uri(url) if request else url


class PropertyListSerializer(serializers.ModelSerializer):
    """Compact representation used in search results / listing grids."""

    agency = AgencyMinimalSerializer(read_only=True)
    primary_image = serializers.SerializerMethodField()
    is_stale = serializers.BooleanField(read_only=True)

    class Meta:
        model = Property
        fields = [
            "id",
            "title",
            "property_type",
            "transaction_type",
            "price",
            "currency",
            "price_period",
            "location",
            "state",
            "city",
            "area",
            "bedrooms",
            "bathrooms",
            "toilets",
            "furnished_status",
            "status",
            "verification_status",
            "is_stale",
            "is_featured",
            "live_viewing_available",
            "agency",
            "primary_image",
            "discovered_at",
        ]

    def get_primary_image(self, obj):
        image = obj.images.filter(display_authorized=True).order_by("order").first()
        if not image:
            return None
        return PropertyImageSerializer(image, context=self.context).data


class PropertyDetailSerializer(PropertyListSerializer):
    """Full representation for the property detail page."""

    images = serializers.SerializerMethodField()
    source_name = serializers.SerializerMethodField()

    class Meta(PropertyListSerializer.Meta):
        fields = PropertyListSerializer.Meta.fields + [
            "description",
            "amenities",
            "latitude",
            "longitude",
            "source_url",
            "source_name",
            "last_checked_at",
            "last_seen_at",
            "images",
        ]

    def get_images(self, obj):
        images = obj.images.filter(display_authorized=True).order_by("order")
        return PropertyImageSerializer(images, many=True, context=self.context).data

    def get_source_name(self, obj):
        return obj.source.name if obj.source_id else ""
