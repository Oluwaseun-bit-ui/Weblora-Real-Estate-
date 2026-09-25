from unittest import mock

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.web_search import services

pytestmark = pytest.mark.django_db

PAGE = """
<html><body>
  <a href="tel:0803 123 4567">Call</a>
  <a href="mailto:sales@lekkihomes.ng">Email</a>
  <a href="https://wa.me/2348091234567">WhatsApp</a>
  <p>Or call +234 902 555 1212. Logo: logo@2x.png</p>
</body></html>
"""


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()


def test_build_query_from_filters():
    q = services.build_query(
        {"location": "Lekki", "transaction_type": "RENT", "property_type": "APARTMENT", "bedrooms": "2"}
    )
    assert q == "2 bedroom apartment for rent in Lekki Lagos agent contact"


def test_extract_contacts_finds_phone_email_whatsapp():
    contacts = services.extract_contacts(PAGE)
    assert contacts["phones"] == ["+2348031234567", "+2349025551212"]
    assert contacts["emails"] == ["sales@lekkihomes.ng"]
    assert contacts["whatsapp"] == ["2348091234567"]


def test_fetch_page_refuses_private_addresses():
    with mock.patch.object(services.requests, "get") as get:
        assert services.fetch_page("http://127.0.0.1/admin") == ""
        assert services.fetch_page("file:///etc/passwd") == ""
        get.assert_not_called()


def test_endpoint_reports_not_configured_without_key(settings):
    settings.BRAVE_SEARCH_API_KEY = ""
    resp = APIClient().get("/api/web-search/", {"location": "Lekki"})
    assert resp.status_code == 200
    assert resp.data == {"available": False, "reason": "not_configured", "results": []}


def test_endpoint_returns_unverified_results_with_contacts(settings):
    settings.BRAVE_SEARCH_API_KEY = "test-key"
    brave_results = [{"title": "2 Bed in <strong>Lekki</strong>", "url": "https://lekkihomes.ng/x", "site": "lekkihomes.ng", "snippet": "Nice"}]
    with mock.patch.object(services, "brave_search", return_value=brave_results) as brave, mock.patch.object(
        services, "fetch_page", return_value=PAGE
    ):
        resp = APIClient().get("/api/web-search/", {"location": "Lekki"})
        APIClient().get("/api/web-search/", {"location": "Lekki"})  # served from cache

    assert brave.call_count == 1
    assert resp.data["available"] is True
    result = resp.data["results"][0]
    assert result["verified"] is False
    assert result["contacts"]["phones"][0] == "+2348031234567"
