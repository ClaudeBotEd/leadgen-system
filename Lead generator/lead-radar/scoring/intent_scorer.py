"""Intent scorer — heuristische lead kwalificatie zonder LLM.

Score 0-100 op basis van:
  - keyword_density:  hoe vaak komen niche keywords voor op homepage
  - contact_quality:  named email > info@ > geen email
  - page_quality:     heeft contact + about + portfolio paginas
  - location_match:   stad in adres komt overeen met query locatie
  - company_size:     SMB indicators
  - website_modern:   HTTPS + responsive

Returns (score, breakdown) zodat je per lead ziet WAAR de score vandaan komt.
"""

from __future__ import annotations
import re
from pathlib import Path
import yaml


_KEYWORDS_CACHE: dict | None = None


def load_keywords(path: str | Path | None = None) -> dict:
    global _KEYWORDS_CACHE
    if _KEYWORDS_CACHE is not None and path is None:
        return _KEYWORDS_CACHE
    if path is None:
        path = Path(__file__).resolve().parent.parent / "keywords.yaml"
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    _KEYWORDS_CACHE = data
    return data


def score_lead(
    lead: dict,
    niche: str = "warmtepomp",
    location: str = "",
    config: dict | None = None,
    keywords: dict | None = None,
) -> tuple[int, dict]:
    """Score een verrijkte lead. Returns (0-100, breakdown_dict)."""
    config = config or {}
    weights = config.get("scoring", {}).get("weights", {
        "keyword_density": 30,
        "contact_quality": 20,
        "page_quality": 15,
        "location_match": 15,
        "company_size": 10,
        "website_modern": 10,
    })
    kw = keywords or load_keywords()

    breakdown = {
        "keyword_density": _score_keyword_density(lead, niche, kw, max_points=weights["keyword_density"]),
        "contact_quality": _score_contact_quality(lead, max_points=weights["contact_quality"]),
        "page_quality": _score_page_quality(lead, max_points=weights["page_quality"]),
        "location_match": _score_location_match(lead, location, kw, max_points=weights["location_match"]),
        "company_size": _score_company_size(lead, kw, max_points=weights["company_size"]),
        "website_modern": _score_website_modern(lead, max_points=weights["website_modern"]),
    }

    total = sum(breakdown.values())
    total = max(0, min(100, int(round(total))))
    return total, breakdown


def _score_keyword_density(lead: dict, niche: str, kw: dict, max_points: int) -> float:
    """Hoe vaak komt de niche term voor op homepage."""
    text = (lead.get("homepage_text") or "").lower()
    if not text:
        return 0.0

    industry_terms = kw.get("industry_terms", {}).get(niche, [])
    if not industry_terms:
        industry_terms = kw.get("industry_terms", {}).get("hvac", [])

    count = 0
    for term in industry_terms:
        count += len(re.findall(r"\b" + re.escape(term.lower()) + r"\b", text))

    if count == 0:
        return 0.0
    if count <= 2:
        return max_points * 0.3
    if count <= 5:
        return max_points * 0.6
    if count <= 10:
        return max_points * 0.9
    return float(max_points)


def _score_contact_quality(lead: dict, max_points: int) -> float:
    """Beoordeel email kwaliteit."""
    email = (lead.get("email") or "").lower()
    if not email:
        return 0.0

    local = email.split("@")[0]

    if "." in local and 3 <= len(local) <= 25:
        return float(max_points)
    if local.isalpha() and 3 <= len(local) <= 12:
        return max_points * 0.85
    if local in ("sales", "support", "klantenservice", "service"):
        return max_points * 0.6
    if local in ("info", "contact", "office", "hello", "hallo"):
        return max_points * 0.5
    return max_points * 0.3


def _score_page_quality(lead: dict, max_points: int) -> float:
    """Heeft de site contact + about + portfolio paginas."""
    has = 0
    if lead.get("has_contact"):
        has += 1
    if lead.get("has_about"):
        has += 1
    if lead.get("has_portfolio"):
        has += 1
    return (has / 3.0) * max_points


def _score_location_match(lead: dict, location: str, kw: dict, max_points: int) -> float:
    """Komt de query locatie voor in adres/homepage?"""
    if not location:
        return max_points * 0.5

    location = location.lower()
    haystack = " ".join([
        (lead.get("address") or ""),
        (lead.get("city") or ""),
        (lead.get("homepage_text") or "")[:5000],
    ]).lower()

    variants = kw.get("location_variants", {}).get(location, [location])

    for variant in variants:
        if variant.lower() in haystack:
            return float(max_points)

    return 0.0


def _score_company_size(lead: dict, kw: dict, max_points: int) -> float:
    """SMB indicators — wil je niet te groot (Vaillant/Daikin) en niet te klein."""
    text = (lead.get("homepage_text") or "").lower()
    if not text:
        return 0.0

    too_big = kw.get("negative_indicators", {}).get("too_big", [])
    not_installer = kw.get("negative_indicators", {}).get("not_installer", [])

    big_signals = sum(1 for term in too_big if term.lower() in text)
    fab_signals = sum(1 for term in not_installer if term.lower() in text)

    penalty = (big_signals * 0.2) + (fab_signals * 0.4)

    positive = 0.0
    if lead.get("kvk_number") or lead.get("kbo_number") or lead.get("btw_number"):
        positive += 0.5

    score = max(0.0, max_points * (positive - penalty))
    return min(float(max_points), score)


def _score_website_modern(lead: dict, max_points: int) -> float:
    """HTTPS + heeft homepage_text content."""
    score = 0.0
    if lead.get("has_https"):
        score += max_points * 0.5
    text_len = len(lead.get("homepage_text") or "")
    if text_len > 1000:
        score += max_points * 0.5
    elif text_len > 200:
        score += max_points * 0.25
    return min(float(max_points), score)


def filter_low_score(leads: list[dict], min_score: int = 30) -> list[dict]:
    """Filter leads met score < min_score."""
    return [lead for lead in leads if lead.get("intent_score", 0) >= min_score]


if __name__ == "__main__":
    sample = {
        "company_name": "Voorbeeld Installatie BV",
        "domain": "voorbeeld-installatie.nl",
        "url": "https://voorbeeld-installatie.nl",
        "email": "jan.devries@voorbeeld-installatie.nl",
        "phone": "+31 20 1234567",
        "address": "1011 AB Amsterdam",
        "city": "Amsterdam",
        "country": "NL",
        "kvk_number": "12345678",
        "has_contact": True,
        "has_about": True,
        "has_portfolio": True,
        "has_https": True,
        "homepage_text": (
            "Wij zijn warmtepomp specialisten in Amsterdam. Hybride warmtepomp, "
            "lucht-water warmtepomp installatie. ISDE subsidie aanvragen. "
            "Bosch warmtepompen, Daikin warmtepompen. Over ons. Contact. "
            "Onze projecten en referenties."
        ) * 3,
    }
    score, breakdown = score_lead(sample, niche="warmtepomp", location="amsterdam")
    print(f"Score: {score}/100")
    for k, v in breakdown.items():
        print(f"  {k}: {v:.1f}")
