"""Website scraper — bezoekt een company website en haalt contactinfo op.

Doet:
- GET op homepage
- Vindt links naar /contact, /over-ons, /about
- Extract emails, telefoon, adres, bedrijfsnaam
- Bepaalt page features (heeft about, contact, projects)

Returns dict klaar voor scoring.
"""

from __future__ import annotations
import re
import sys
from pathlib import Path
from urllib.parse import urljoin, urlparse
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.email_extractor import extract_emails, rank_emails  # noqa: E402
from utils.rate_limiter import RateLimiter  # noqa: E402


PHONE_RE = re.compile(
    r"(?:\+31|0031|0|\+32|0032)\s?[-.\s]?(?:\d[-.\s]?){8,10}\d"
)

KVK_RE = re.compile(r"\bKvK[\s:.-]*([0-9]{8})\b", re.IGNORECASE)
KBO_RE = re.compile(r"\b(?:BTW|VAT|KBO|BCE)[\s:.-]*BE\s?([0-9]{4}[\s.]?[0-9]{3}[\s.]?[0-9]{3})\b", re.IGNORECASE)
BTW_NL_RE = re.compile(r"\bNL\s?([0-9]{9})B[0-9]{2}\b", re.IGNORECASE)

POSTCODE_NL_RE = re.compile(r"\b([1-9][0-9]{3})\s?([A-Z]{2})\b\s+([A-Z][a-zA-Z\s\-']+)")
POSTCODE_BE_RE = re.compile(r"\b([1-9][0-9]{3})\s+([A-Z][a-zA-Z\s\-']+)")

CONTACT_PATHS = [
    "/contact", "/contact/", "/contact-us", "/contact-ons",
    "/contacteer-ons", "/neem-contact-op",
    "/over-ons", "/over-ons/", "/over", "/about", "/about-us",
    "/over-mij", "/wie-zijn-wij",
]

DEFAULT_TIMEOUT = 15
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def fetch_page(url: str, timeout: int = DEFAULT_TIMEOUT, user_agent: str = DEFAULT_USER_AGENT) -> tuple[str, str] | None:
    """Fetch een URL. Returns (final_url, html) of None bij fout."""
    headers = {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "nl-NL,nl;q=0.9,en;q=0.8",
    }
    try:
        resp = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        if resp.status_code != 200:
            return None
        if "text/html" not in resp.headers.get("Content-Type", ""):
            return None
        return resp.url, resp.text
    except (requests.RequestException, requests.Timeout):
        return None


def extract_company_data(url: str, rate_limiter: RateLimiter | None = None, max_subpages: int = 3) -> dict:
    """Volledige website analyse — homepage + max N subpaginas (contact, over-ons).

    Returns dict met velden:
      - company_name, domain, url, email, contact_name, phone, address, city, country
      - kvk_number, btw_number, kbo_number
      - has_contact, has_about, has_portfolio, has_https
      - homepage_text
      - scraped_at (ISO 8601)
    """
    limiter = rate_limiter or RateLimiter(min_delay=2.0)
    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    domain = parsed.netloc.lower().replace("www.", "")

    out = {
        "company_name": "",
        "domain": domain,
        "url": url,
        "email": "",
        "all_emails": [],
        "contact_name": "",
        "phone": "",
        "address": "",
        "city": "",
        "country": "",
        "kvk_number": "",
        "btw_number": "",
        "kbo_number": "",
        "has_contact": False,
        "has_about": False,
        "has_portfolio": False,
        "has_https": parsed.scheme == "https",
        "homepage_text": "",
        "scraped_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }

    limiter.wait(domain)
    home = fetch_page(url)
    if not home:
        return out

    final_url, html = home
    out["url"] = final_url
    soup = BeautifulSoup(html, "html.parser")

    title = soup.find("title")
    if title and title.text:
        out["company_name"] = title.text.strip().split("|")[0].split("-")[0].strip()[:120]

    for s in soup(["script", "style", "noscript"]):
        s.decompose()
    home_text = soup.get_text(separator=" ", strip=True)[:50_000]
    out["homepage_text"] = home_text

    _harvest(html, home_text, soup, base, out)

    candidates = _find_contact_links(soup, base)
    visited_count = 0
    for sub_url in candidates:
        if visited_count >= max_subpages:
            break
        if sub_url == final_url:
            continue
        limiter.wait(domain)
        page = fetch_page(sub_url)
        if not page:
            continue
        sub_final_url, sub_html = page
        sub_soup = BeautifulSoup(sub_html, "html.parser")
        for s in sub_soup(["script", "style", "noscript"]):
            s.decompose()
        sub_text = sub_soup.get_text(separator=" ", strip=True)[:50_000]
        _harvest(sub_html, sub_text, sub_soup, base, out)
        visited_count += 1

    if out["all_emails"]:
        ranked = rank_emails(out["all_emails"])
        out["email"] = ranked[0] if ranked else ""

    if out["domain"].endswith(".nl") or out["kvk_number"]:
        out["country"] = "NL"
    elif out["domain"].endswith(".be") or out["kbo_number"]:
        out["country"] = "BE"

    return out


def _harvest(html: str, text: str, soup: BeautifulSoup, base: str, out: dict) -> None:
    """Harvest data uit een pagina en update `out` dict in place."""
    new_emails = extract_emails(html) + extract_emails(text)
    out["all_emails"] = sorted(set(out["all_emails"]) | set(new_emails))

    if not out["phone"]:
        phone_match = PHONE_RE.search(text)
        if phone_match:
            out["phone"] = re.sub(r"\s+", " ", phone_match.group(0)).strip()

    if not out["kvk_number"]:
        m = KVK_RE.search(text)
        if m:
            out["kvk_number"] = m.group(1)
    if not out["kbo_number"]:
        m = KBO_RE.search(text)
        if m:
            out["kbo_number"] = m.group(1).replace(" ", "").replace(".", "")
    if not out["btw_number"]:
        m = BTW_NL_RE.search(text)
        if m:
            out["btw_number"] = m.group(1)

    if not out["city"]:
        m = POSTCODE_NL_RE.search(text)
        if m:
            out["address"] = f"{m.group(1)} {m.group(2)} {m.group(3).strip()}".strip()
            out["city"] = m.group(3).strip().split()[0]
        else:
            m = POSTCODE_BE_RE.search(text)
            if m:
                out["address"] = f"{m.group(1)} {m.group(2).strip()}".strip()
                out["city"] = m.group(2).strip().split()[0]

    text_low = text.lower()
    if any(p in text_low for p in ("contact", "neem contact", "offerte aanvragen", "afspraak maken")):
        out["has_contact"] = True
    if any(p in text_low for p in ("over ons", "over mij", "ons team", "wie zijn wij", "about us")):
        out["has_about"] = True
    if any(p in text_low for p in ("projecten", "referenties", "ons werk", "case studies", "realisaties")):
        out["has_portfolio"] = True


def _find_contact_links(soup: BeautifulSoup, base: str) -> list[str]:
    """Vind links naar /contact, /over-ons paginas op homepage."""
    found = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith("#") or href.startswith("javascript:") or href.startswith("mailto:"):
            continue
        href_low = href.lower()
        for path in CONTACT_PATHS:
            if path in href_low:
                full = urljoin(base, href)
                if full not in found:
                    found.append(full)
                break
    return found


def enrich_results(results: list[dict], rate_limiter: RateLimiter | None = None, max_subpages: int = 3) -> list[dict]:
    """Verrijk een lijst search-resultaten met website data."""
    enriched: list[dict] = []
    for i, r in enumerate(results, 1):
        url = r.get("url")
        if not url:
            continue
        print(f"[website] [{i}/{len(results)}] {url}")
        try:
            data = extract_company_data(url, rate_limiter=rate_limiter, max_subpages=max_subpages)
            data["title"] = r.get("title", "")
            data["snippet"] = r.get("snippet", "")
            data["source"] = r.get("source", "website")
            data["query"] = r.get("query", "")
            enriched.append(data)
        except Exception as e:
            print(f"[website] fout: {e}")
            continue
    return enriched


if __name__ == "__main__":
    test = extract_company_data("https://example.com/")
    print(test)
