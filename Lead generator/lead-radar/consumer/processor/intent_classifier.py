"""Intent classifier — pre-filter: lead vs info vs promo.

Werkt rule-based zodat het 100% offline draait.  Voorbeelden:
- "wat is een warmtepomp"             -> info  (skip)
- "wij plaatsen warmtepompen"          -> promo (skip)
- "iemand een goede installateur in U" -> lead  (keep)
"""
from __future__ import annotations

import re

LEAD_SIGNALS = [
    r"\b(zoek|gezocht|wie kan|wie heeft|iemand een|iemand tip|tip nodig|advies nodig|hulp nodig|help nodig|raden|aanrader|aanraden)\b",
    r"\b(offerte|offertes|prijsopgave|kostenraming|aanbieding|prijzen)\b",
    r"\b(installateur|installatiebedrijf|monteur|vakman|aannemer|specialist|technieker|techneut)\b",
    r"\b(kapot|stuk|defect|werkt niet|storing|lekt|lekkage|gaat stuk|moet vervangen|aan vervanging|verouderd)\b",
    r"\b(laten plaatsen|laten installeren|laten aanleggen|laten doen|laten vervangen|laten aansluiten)\b",
    r"\b(welke kiezen|welk merk|welk model|advies welke|hulp keuze|kiezen tussen|twijfel tussen)\b",
    r"\b(z\.?s\.?m\.?|asap|spoed|dringend|haast|deze week|deze maand|binnenkort|vandaag|morgen|volgende week|met spoed)\b",
]

PROMO_SIGNALS = [
    r"\b(wij plaatsen|wij installeren|wij bieden|wij verzorgen|wij leveren|onze monteurs|ons bedrijf|onze specialiteit|al \d+ jaar ervaring)\b",
    r"\b(neem contact op|bel ons|bel naar|mail ons|stuur een mail|whatsapp ons|onze website|onze diensten|ons aanbod)\b",
    r"\b(gratis offerte|gratis advies|geheel vrijblijvend|vrijblijvend offerte)\b.*\b(via ons|bij ons|onze)\b",
]

INFO_SIGNALS = [
    r"^\s*(wat is|wat zijn|hoe werkt|hoe werken|wat doet|waarom|verschil tussen|voor- en nadelen|review van|test van|uitleg|samenvatting)\b",
    r"\b(wikipedia|wiki-pagina|encyclopedie)\b",
]

_RE_LEAD = [re.compile(p, re.IGNORECASE) for p in LEAD_SIGNALS]
_RE_PROMO = [re.compile(p, re.IGNORECASE) for p in PROMO_SIGNALS]
_RE_INFO = [re.compile(p, re.IGNORECASE) for p in INFO_SIGNALS]


def classify_post_kind(text: str) -> str:
    """'lead' | 'promo' | 'info' | 'unknown'."""
    if not text:
        return "unknown"
    promo_hits = sum(1 for r in _RE_PROMO if r.search(text))
    info_hits = sum(1 for r in _RE_INFO if r.search(text))
    lead_hits = sum(1 for r in _RE_LEAD if r.search(text))

    if promo_hits >= 2:
        return "promo"
    if info_hits >= 1 and lead_hits == 0:
        return "info"
    if lead_hits >= 1:
        return "lead"
    if promo_hits >= 1:
        return "promo"
    return "unknown"


def is_potential_lead(text: str) -> bool:
    """True als waarschijnlijk een echte lead-vraag is.

    Strikt: filtert direct 'promo' en 'info' weg.  'unknown' blijft —
    de scorer beslist dan o.b.v. keywords + locatie + urgency.
    """
    kind = classify_post_kind(text)
    return kind in {"lead", "unknown"}
