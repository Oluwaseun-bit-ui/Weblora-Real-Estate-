from django.utils import timezone
from rest_framework import serializers

from apps.properties.models import Property

from .models import Lead


class LeadCreateSerializer(serializers.ModelSerializer):
    property_id = serializers.PrimaryKeyRelatedField(
        source="property", queryset=Property.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = Lead
        fields = [
            "id",
            "property_id",
            "agency",
            "customer_name",
            "customer_email",
            "customer_phone",
            "message",
            "source_channel",
            "consent_given",
            "status",
            "created_at",
        ]
        read_only_fields = ["id", "status", "created_at"]

    def validate(self, attrs):
        if not attrs.get("customer_email") and not attrs.get("customer_phone"):
            raise serializers.ValidationError("Provide at least an email or a phone number so the agency can reach you.")
        if not attrs.get("consent_given"):
            raise serializers.ValidationError(
                {"consent_given": "You must consent to your details being shared with the agency to submit an enquiry."}
            )
        return attrs

    def create(self, validated_data):
        validated_data["consent_timestamp"] = timezone.now()
        validated_data["status"] = Lead.Status.NEW
        return super().create(validated_data)
