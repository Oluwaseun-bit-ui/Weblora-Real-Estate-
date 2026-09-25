"""
Option A: live "More results from the web" alongside our own listings.

1. Build a plain-English query from the customer's search filters.
2. Ask the Brave Search API for matching pages.
3. Visit each result page once (like a link preview) and pull out explicit
   contact details: tel:/mailto:/WhatsApp links and Nigerian phone numbers.

Results are NOT verified and are always labelled as such in the API and UI.
Responses are cached so repeated searches don't spend Brave quota.
"""
import hashlib
import html
import ipaddress
import logging
import re
import socket
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import unquote, urljoin, urlparse

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger("apps.web_search")

BRAVE_ENDPOINT = "https://api.search.brave.com/res/v1/web/search"
USER_AGENT = "WebloraBot/1.0 (+https://github.com/Oluwaseun-bit-ui/Weblora-Real-Estate-)"
PAGE_TIMEOUT_SECONDS = 5
PAGE_MAX_BYTES = 1_000_000
MAX_REDIRECTS = 3
MAX_CONTACTS_PER_KIND = 3

TRANSACTION_WORDS = {"RENT": "for rent", "BUY": "for sale", "SHORTLET": "shortlet"}
TYPE_WORDS = {
    "APARTMENT": "apartment", "HOUSE": "house", "DUPLEX": "duplex", "BUNGALOW": "bungalow",
    "TERRACE": "terrace", "LAND": "land", "SHORTLET": "shortlet apartment", "COMMERCIAL": "commercial property",
}

TAG_RE = re.compile(r"<[^>]+>")
TEL_RE = re.compile(r'href=["\']tel:([^"\']+)["\']', re.I)
MAILTO_RE = re.compile(r'href=["\']mailto:([^"\'?]+)', re.I)
WHATSAPP_RE = re.compile(r"(?:wa\.me/|api\.whatsapp\.com/send\?phone=|whatsapp\.com/send/?\?phone=)\+?(\d{10,15})", re.I)
# Nigerian mobile numbers: 0803 123 4567 / +234 803 123 4567 / 234-803-123-4567
NG_PHONE_RE = re.compile(r"(?<!\d)(?:\+?234[\s-]?|0)([789][01]\d)[\s-]?(\d{3})[\s-]?(\d{4})(?!\d)")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
NOT_EMAIL_SUFFIXES = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".css", ".js")


class WebSearchNotConfigured(Exception):
    pass


def build_query(filters) -> str:
    parts = []
    if filters.get("q"):
        parts.append(filters["q"].strip())
    if filters.get("bedrooms"):
        parts.append(f"{filters['bedrooms']} bedroom")
    if filters.get("furnished_status") == "FURNISHED":
        parts.append("furnished")
    parts.append(TYPE_WORDS.get(filters.get("property_type", ""), "property"))
    parts.append(TRANSACTION_WORDS.get(filters.get("transaction_type", ""), ""))
    location = (filters.get("location") or "").strip()
    parts.append(f"in {location} Lagos" if location and "lagos" not in location.lower() else f"in {location or 'Lagos'}")
    parts.append("agent contact")
    return " ".join(p for p in parts if p)


def _normalize_ng_phone(match) -> str:
    return "+234" + "".join(match.groups())


def _is_public_host(hostname) -> bool:
    try:
        infos = socket.getaddrinfo(hostname, None)
    except (socket.gaierror, UnicodeError):
        return False
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            return False
    return True


def fetch_page(url, session=None) -> str:
    """GET a public web page safely: http(s) only, public IPs only, size and time capped."""
    session = session or requests
    for _ in range(MAX_REDIRECTS + 1):
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname or not _is_public_host(parsed.hostname):
            return ""
        resp = session.get(
            url, headers={"User-Agent": USER_AGENT}, timeout=PAGE_TIMEOUT_SECONDS, allow_redirects=False, stream=True
        )
        if resp.is_redirect and resp.headers.get("location"):
            url = urljoin(url, resp.headers["location"])
            resp.close()
            continue
        if resp.status_code != 200 or "html" not in resp.headers.get("content-type", ""):
            resp.close()
            return ""
        body = b""
        for chunk in resp.iter_content(64 * 1024):
            body += chunk
            if len(body) >= PAGE_MAX_BYTES:
                break
        resp.close()
        return body.decode(resp.encoding or "utf-8", errors="replace")
    return ""


def _dedupe(values):
    out = []
    for v in values:
        if v and v not in out:
            out.append(v)
    return out[:MAX_CONTACTS_PER_KIND]


def extract_contacts(page_html) -> dict:
    text = html.unescape(TAG_RE.sub(" ", page_html))
    phones = []
    for raw in TEL_RE.findall(page_html):
        m = NG_PHONE_RE.search(unquote(raw))
        phones.append(_normalize_ng_phone(m) if m else unquote(raw).strip())
    phones += [_normalize_ng_phone(m) for m in NG_PHONE_RE.finditer(text)]

    emails = [unquote(e).strip() for e in MAILTO_RE.findall(page_html)] + EMAIL_RE.findall(text)
    emails = [e for e in emails if not e.lower().endswith(NOT_EMAIL_SUFFIXES)]

    return {
        "phones": _dedupe(phones),
        "emails": _dedupe(e.lower() for e in emails),
        "whatsapp": _dedupe(WHATSAPP_RE.findall(page_html)),
    }


def _contacts_for(result):
    try:
        return extract_contacts(fetch_page(result["url"]))
    except requests.RequestException:
        return {"phones": [], "emails": [], "whatsapp": []}


def brave_search(query, count):
    api_key = settings.BRAVE_SEARCH_API_KEY
    if not api_key:
        raise WebSearchNotConfigured("BRAVE_SEARCH_API_KEY is not set.")
    resp = requests.get(
        BRAVE_ENDPOINT,
        params={"q": query, "count": count, "safesearch": "moderate"},
        headers={"Accept": "application/json", "X-Subscription-Token": api_key},
        timeout=10,
    )
    resp.raise_for_status()
    results = []
    for item in (resp.json().get("web") or {}).get("results") or []:
        url = item.get("url") or ""
        results.append(
            {
                "title": html.unescape(TAG_RE.sub("", item.get("title") or "")),
                "url": url,
                "site": (item.get("meta_url") or {}).get("hostname") or urlparse(url).hostname or "",
                "snippet": html.unescape(TAG_RE.sub("", item.get("description") or "")),
            }
        )
    return results


def search_web(filters) -> dict:
    query = build_query(filters)
    cache_key = "web_search:" + hashlib.sha256(query.lower().encode()).hexdigest()
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    results = brave_search(query, settings.WEB_SEARCH_RESULT_COUNT)
    with ThreadPoolExecutor(max_workers=6) as pool:
        for result, contacts in zip(results, pool.map(_contacts_for, results)):
            result["contacts"] = contacts
            result["verified"] = False

    payload = {"query": query, "results": results}
    cache.set(cache_key, payload, settings.WEB_SEARCH_CACHE_SECONDS)
    return payload
