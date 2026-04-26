"""Scorer — geeft 0-100 lead-score volgens spec:

  +20  locatie aanwezig  (stad of postcode)
  +25  urgentie (zsm, deze maand, asap, dringend, …)
  +25  vraagt expliciet installateur/monteur/aannemer
  +15  woning/situatie genoemd (huis, m2, bouwjaar, dak, …)
  +15  budget/offerte genoemd (euro, prijs, offerte, …)

>=70 hot, 40-69 warm, <40 cold.  Cap op 100.
"""
from __future__ import annotations

import re

_RE_URGENCY = re.compile(
    r"\b(z\.?s\.?m\.?|asap|spoed|dringend|haast|"
    r"deze week|deze maand|binnenkort|vandaag|morgen|volgende week|"
    r"met spoed|snel mogelijk|liefst snel|liefst nog deze)\b",
    re.IGNORECASE,
)
_RE_INSTALLER = re.compile(
    r"\b(installateur|installatiebedrijf|monteur|vakman|aannemer|specialist|"
    r"technieker|techneut|cv\-?monteur|verwarmingsmonteur|hvac\-?bedrijf)\b",
    re.IGNORECASE,
)
_RE_HOME = re.compile(
    r"\b(huis|woning|appartement|rijtjeshuis|tussenwoning|hoekwoning|"
    r"vrijstaand|twee[\s\-]?onder[\s\-]?een[\s\-]?kap|geschakelde woning|"
    r"m2|m²|m\^2|vierkante meter|bouwjaar|gebouw|dak|verdieping|"
    r"kruipruimte|kelder|badkamer|keuken|woonkamer|slaapkamer|cv\-ruimte|"
    r"meterkast|zolder|garage)\b",
    re.IGNORECASE,
)
_RE_BUDGET = re.compile(
    r"(\beuro\b|€|\bEUR\b|"
    r"\b(?:budget|prijs|prijzen|kosten|bedrag|kostenraming|prijsopgave|"
    r"offerte|offertes|aanbieding|aanbod|investering|tarief)\b|"
    r"\b\d{1,3}(?:[\.\,\s]\d{3})*\s?(?:k|euro|€))",
    re.IGNORECASE,
)


def _score_location(city: str | None, lower: str) -> int:
    if city:
        return 20
    if re.search(r"\b\d{4}\s?[a-zA-Z]{2}\b", lower):
        return 20
    return 0


def _score_urgency(text: str) -> int:
    return 25 if _RE_URGENCY.search(text) else 0


def _score_installer(text: str) -> int:
    return 25 if _RE_INSTALLER.search(text) else 0


def _score_home(text: str) -> int:
    return 15 if _RE_HOME.search(text) else 0


def _score_budget(text: str) -> int:
    return 15 if _RE_BUDGET.search(text) else 0


def score_post(cleaned: dict, niche_keywords: list[str] | None = None) -> tuple[int, dict[str, int]]:
    """Bereken score + breakdown.

    `cleaned` is output van processor.cleaner.clean_post().
    `niche_keywords` is optioneel — als geen enkel keyword voorkomt drukken
    we 30 punten af om totaal off-topic posts uit de top te houden.
    """
    text = cleaned.get("full_no_url", "") or cleaned.get("full", "")
    lower = cleaned.get("lower", text.lower())
    city = cleaned.get("city")

    breakdown = {
        "location": _score_location(city, lower),
        "urgency": _score_urgency(text),
        "installer": _score_installer(text),
        "situation": _score_home(text),
        "budget": _score_budget(text),
    }
    total = sum(breakdown.values())

    if niche_keywords:
        if not any(kw.lower() in lower for kw in niche_keywords):
            total = max(0, total - 30)
            breakdown["off_topic_penalty"] = -30

    total = max(0, min(100, total))
    return total, breakdown
