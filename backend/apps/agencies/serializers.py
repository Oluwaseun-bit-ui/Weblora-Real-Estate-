from rest_framework import serializers

from .models import Agency


class AgencyPublicSerializer(serializers.ModelSerializer):
    """What customers see on an agency's public page / listing cards."""

    verification_badges = serializers.SerializerMethodField()
    logo_url = serializers.SerializerMethodField()

    class Meta:
        model = Agency
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "logo_url",
            "website",
            "phone_number",
            "email",
            "whatsapp_number",
            "service_locations",
            "verification_status",
            "verification_badges",
        ]

    def get_verification_badges(self, obj):
        return obj.verification_badges()

    def get_logo_url(self, obj):
        if obj.logo and obj.logo_display_authorized:
            request = self.context.get("request")
            url = obj.logo.url
            return request.build_absolute_uri(url) if request else url
        return None


class AgencyMinimalSerializer(serializers.ModelSerializer):
    """Compact agency info embedded in property search results."""

    verification_badges = serializers.SerializerMethodField()

    class Meta:
        model = Agency
        fields = ["id", "name", "slug", "verification_status", "verification_badges"]

    def get_verification_badges(self, obj):
        return obj.verification_badges()
