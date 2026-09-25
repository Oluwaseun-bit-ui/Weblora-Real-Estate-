from rest_framework import serializers

from apps.properties.models import Property

from .models import LiveViewingRequest, LiveViewingSession


class LiveViewingRequestCreateSerializer(serializers.ModelSerializer):
    property_id = serializers.PrimaryKeyRelatedField(source="property", queryset=Property.objects.all())

    class Meta:
        model = LiveViewingRequest
        fields = [
            "id",
            "property_id",
            "customer_name",
            "customer_email",
            "customer_phone",
            "requested_date",
            "requested_time",
            "customer_message",
            "status",
            "created_at",
        ]
        read_only_fields = ["id", "status", "created_at"]

    def validate_property_id(self, property_obj):
        if not property_obj.live_viewing_available:
            raise serializers.ValidationError("Live viewing is not available for this property.")
        return property_obj

    def validate(self, attrs):
        if not attrs.get("customer_email") and not attrs.get("customer_phone"):
            raise serializers.ValidationError("Provide at least an email or a phone number so we can reach you about this viewing.")
        return attrs


class LiveViewingRequestStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = LiveViewingRequest
        fields = [
            "id",
            "status",
            "requested_date",
            "requested_time",
            "accepted_at",
            "started_at",
            "ended_at",
        ]


class RoomTokenSerializer(serializers.Serializer):
    room_id = serializers.CharField()
    token = serializers.CharField()
    provider = serializers.CharField()
    expires_in_seconds = serializers.IntegerField()
    role = serializers.CharField()
