"""Shared test factories (factory_boy) used across app test suites."""
import factory
from django.utils import timezone

from apps.accounts.models import User
from apps.agencies.models import Agency
from apps.properties.models import Property
from apps.sources.models import PropertySource


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.Sequence(lambda n: f"user{n}@example.com")
    role = User.Role.VERIFICATION_OFFICER
    is_staff = True


class PropertySourceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PropertySource

    name = factory.Sequence(lambda n: f"Source {n}")
    source_type = PropertySource.SourceType.MANUAL
    ingestion_method = PropertySource.IngestionMethod.MANUAL_ENTRY
    permission_status = PropertySource.PermissionStatus.AUTHORIZED
    is_active = True


class AgencyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Agency

    name = factory.Sequence(lambda n: f"Agency {n}")
    phone_number = "+2348010000000"
    email = factory.Sequence(lambda n: f"agency{n}@example.com")


class PropertyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Property

    title = factory.Sequence(lambda n: f"2 Bedroom Apartment {n}")
    property_type = Property.PropertyType.APARTMENT
    transaction_type = Property.TransactionType.RENT
    price = 3_000_000
    currency = "NGN"
    location = "Lekki Phase 1"
    state = "Lagos"
    city = "Lagos"
    area = "Lekki"
    bedrooms = 2
    bathrooms = 2
    status = Property.ListingStatus.ACTIVE
    agency = factory.SubFactory(AgencyFactory)
