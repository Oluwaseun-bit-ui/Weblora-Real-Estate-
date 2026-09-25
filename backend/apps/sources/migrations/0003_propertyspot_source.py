from django.db import migrations


def create_propertyspot(apps, schema_editor):
    PropertySource = apps.get_model("sources", "PropertySource")
    PropertySource.objects.get_or_create(
        adapter="propertyspot",
        defaults={
            "name": "PropertySpot",
            "url": "https://propertyspot.com.ng/",
            "source_type": "LISTING_PARTNER_FEED",
            "ingestion_method": "PARTNER_FEED",
            "permission_status": "AUTHORIZED",
            "is_active": True,
            "sync_frequency_minutes": 24 * 60,
            "terms_notes": (
                "Owner gave the Weblora founder permission to list PropertySpot properties. "
                "TODO: store the written confirmation here. We never store agents' NIN/BVN/ID fields "
                "that PropertySpot's API exposes."
            ),
        },
    )


def remove_propertyspot(apps, schema_editor):
    apps.get_model("sources", "PropertySource").objects.filter(adapter="propertyspot").delete()


class Migration(migrations.Migration):
    dependencies = [("sources", "0002_propertysource_adapter")]

    operations = [migrations.RunPython(create_propertyspot, remove_propertyspot)]
