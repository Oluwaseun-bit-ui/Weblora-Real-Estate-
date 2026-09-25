from .propertyspot import PropertySpotAdapter

ADAPTERS = {
    "propertyspot": PropertySpotAdapter,
}


def get_adapter(source):
    try:
        return ADAPTERS[source.adapter](source)
    except KeyError:
        raise ValueError(f"No ingestion adapter configured for source {source!r} (adapter={source.adapter!r})")
