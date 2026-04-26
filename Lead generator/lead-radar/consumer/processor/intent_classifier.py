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
    # Marketer-vraagvormen die juist NIEMAND uit de doelgroep gebruikt
    r"\b(zoekt u|zoek je een|wil je besparen|bespaar tot|scherpe prijs|voordelig|laagste prijs|beste prijs|met garantie)\b",
    # Product/sale listings (Marktplaats etc.)
    r"\b(te koop|aangeboden|nieuw in doos|fabrieksnieuw|origineel verpakt|incl\. btw|incl btw|excl\. btw|nieuwprijs)\b",
    r"€\s?\d{2,}",                         # prijs in titel = verkoop, geen vraag
    r"\b(?:vanaf|reeds vanaf|al vanaf)\s+€?\s?\d+\b",
    r"\b(?:bel|app|whatsapp|sms)\s+(?:naar\s+)?\+?\d[\d\s\-]{6,}\b",  # tel-nr in tekst
    # Bedrijfsnamen in titels
    r"\b(b\.?v\.?|bvba|n\.?v\.?|gmbh)\b",
    # Job ads — "monteur gezocht" met salaris/team/fulltime context
    r"\b(vacature|vacatures|in dienst|dienstverband|fulltime|parttime|full[\s\-]?time|part[\s\-]?time|salaris|salariëring|loon|leuk team|aanmelden|wij zoeken|werken bij)\b",
    # Discount/sale promo
    r"\b(\d{1,2}\s?%\s?korting|korting op|kortingsactie|introductieprijs|aanbiedingsprijs|scherp tarief|laagste tarief)\b",
]

# All-caps SHOUTING (vaak job ad of advertentie) — case-sensitive check
_RE_ALLCAPS_TITLE = re.compile(r"^[A-ZÀ-Ý][A-ZÀ-Ý\s\d,\-!\.]{20,}$", re.MULTILINE)

INFO_SIGNALS = [
    r"^\s*(wat is|wat zijn|hoe werkt|hoe werken|wat doet|waarom|verschil tussen|voor- en nadelen|review van|test van|uitleg|samenvatting)\b",
    r"\b(wikipedia|wiki-pagina|encyclopedie)\b",
]

_RE_LEAD = [re.compile(p, re.IGNORECASE) for p in LEAD_SIGNALS]
_RE_PROMO = [re.compile(p, re.IGNORECASE) for p in PROMO_SIGNALS]
_RE_INFO = [re.compile(p, re.IGNORECASE) for p in INFO_SIGNALS]


_RE_STRONG_SEEK = re.compile(
    r"(?:^|\b)(wie kan|wie heeft|iemand een|iemand tip|iemand ervaring|hoe vind ik|"
    r"wie weet|wie kent|kunnen jullie|kun je|tip nodig|advies nodig|hulp nodig|help nodig|"
    r"raden|advies welke|gezocht|gevraagd)\b",
    re.IGNORECASE,
)

# Definitief PROMO — overrullt strong_seek. Vacatures + bedrijfsadvertenties.
_RE_DEFINITIVE_PROMO = re.compile(
    r"\b(vacature|vacatures|in dienst|dienstverband|fulltime|parttime|"
    r"full[\s\-]?time|part[\s\-]?time|salaris|salariëring|loon|leuk team|"
    r"aanmelden|wij zoeken|wij zijn op zoek|werken bij|"
    r"\d{1,2}\s?%\s?korting|introductieprijs|aanbiedingsprijs|"
    r"erkende installateur|gecertificeerd|met garantie|al \d+ jaar)\b",
    re.IGNORECASE,
)


def classify_post_kind(text: str) -> str:
    """'lead' | 'promo' | 'info' | 'unknown'."""
    if not text:
        return "unknown"
    promo_hits = sum(1 for r in _RE_PROMO if r.search(text))
    info_hits = sum(1 for r in _RE_INFO if r.search(text))
    lead_hits = sum(1 for r in _RE_LEAD if r.search(text))
    strong_seek = bool(_RE_STRONG_SEEK.search(text))

    # Extra promo: SHOUTING-titel telt als 1 promo hit
    if _RE_ALLCAPS_TITLE.search(text or ""):
        promo_hits += 1

    # Definitief promo (vacatures, bedrijfsadvertenties) — overrult strong_seek.
    if _RE_DEFINITIVE_PROMO.search(text):
        return "promo"

    # Strong-promo signal in tekst (bv prijs in titel, "zoekt u", telefoonnummer):
    # zelfs een enkele hit telt — tenzij we ook een echte seeker-zin zien.
    if promo_hits >= 1 and not strong_seek:
        return "promo"
    if info_hits >= 1 and lead_hits == 0 and not strong_seek:
        return "info"
    if strong_seek or lead_hits >= 2:
        return "lead"
    if lead_hits >= 1:
        return "lead"
    return "unknown"


def is_potential_lead(text: str) -> bool:
    """True als waarschijnlijk een echte lead-vraag is.

    Strikt: filtert direct 'promo' en 'info' weg.  'unknown' blijft —
    de scorer beslist dan o.b.v. keywords + locatie + urgency.
    """
    kind = classify_post_kind(text)
    return kind in {"lead", "unknown"}
