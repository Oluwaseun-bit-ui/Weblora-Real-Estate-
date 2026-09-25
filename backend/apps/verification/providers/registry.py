from .cac import CACProvider
from .contact import ContactVerificationProvider
from .esvarbon import ESVARBONProvider
from .lasrera import LASRERAProvider
from .website import WebsiteVerificationProvider

#: check_type -> provider class. New regulators/providers register here
#: without touching the verification app's models/views/admin.
PROVIDER_REGISTRY = {
    "ESVARBON": ESVARBONProvider,
    "LASRERA": LASRERAProvider,
    "CAC": CACProvider,
    "WEBSITE": WebsiteVerificationProvider,
    "CONTACT_PHONE": lambda: ContactVerificationProvider.for_channel("phone"),
    "CONTACT_EMAIL": lambda: ContactVerificationProvider.for_channel("email"),
}


def get_provider(check_type: str):
    factory = PROVIDER_REGISTRY.get(check_type)
    if factory is None:
        raise KeyError(f"No verification provider registered for check_type={check_type!r}")
    return factory() if not isinstance(factory, type) else factory()
