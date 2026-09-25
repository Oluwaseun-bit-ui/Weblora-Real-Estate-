import pytest
from django.core.exceptions import ValidationError

from apps.sources.models import PropertySource

pytestmark = pytest.mark.django_db


class TestPropertySourceAuthorization:
    def test_cannot_activate_an_unauthorized_api_source(self):
        source = PropertySource(
            name="Some Agency Feed",
            source_type=PropertySource.SourceType.AGENCY_PARTNER_API,
            ingestion_method=PropertySource.IngestionMethod.API,
            permission_status=PropertySource.PermissionStatus.PENDING_REVIEW,
            is_active=True,
        )
        with pytest.raises(ValidationError):
            source.save()

    def test_manual_entry_source_can_be_active_without_authorization_review(self):
        source = PropertySource(
            name="Ops manual entries",
            source_type=PropertySource.SourceType.MANUAL,
            ingestion_method=PropertySource.IngestionMethod.MANUAL_ENTRY,
            permission_status=PropertySource.PermissionStatus.PENDING_REVIEW,
            is_active=True,
        )
        source.save()
        assert source.pk is not None

    def test_authorized_api_source_can_be_activated(self):
        source = PropertySource(
            name="Partner API",
            source_type=PropertySource.SourceType.AGENCY_PARTNER_API,
            ingestion_method=PropertySource.IngestionMethod.API,
            permission_status=PropertySource.PermissionStatus.AUTHORIZED,
            is_active=True,
        )
        source.save()
        assert source.pk is not None
